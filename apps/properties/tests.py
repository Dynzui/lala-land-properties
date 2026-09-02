from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError

from apps.audittrail.models import AuditEvent

from .models import Development, Location, Property, PropertyType, Variant
from .widgets import MapCoordinateWidget

pytestmark = pytest.mark.django_db


def make_location(**overrides):
    values = {
        "province": "Negros Occidental",
        "city_municipality": "Bacolod",
        "public_label": "Bacolod City, Negros Occidental",
    }
    values.update(overrides)
    return Location.objects.create(**values)


def make_property_type(**overrides):
    values = {
        "name": "Test House and Lot",
        "slug": "test-house-and-lot",
        "applicable_fields": ["bedrooms", "bathrooms", "lot_area_sqm"],
    }
    values.update(overrides)
    return PropertyType.objects.create(**values)


def make_development(location, **overrides):
    values = {
        "name": "The Summit",
        "slug": "the-summit-test",
        "development_type": Development.Type.SUBDIVISION,
        "location": location,
        "summary": "A test development.",
        "description": "A detailed test description.",
    }
    values.update(overrides)
    return Development.objects.create(**values)


def test_public_location_projection_never_contains_private_fields():
    location = make_location(
        street_address_private="123 Private Street",
        latitude_private=Decimal("10.676500"),
        longitude_private=Decimal("122.950900"),
    )

    public = location.as_public_dict()

    assert public["public_label"] == "Bacolod City, Negros Occidental"
    assert "street_address_private" not in public
    assert "latitude_private" not in public
    assert "longitude_private" not in public


def test_approximate_location_requires_explicit_public_coordinates():
    location = Location(
        province="Negros Occidental",
        city_municipality="Bacolod",
        public_label="Bacolod City, Negros Occidental",
        visibility=Location.Visibility.APPROXIMATE,
    )

    with pytest.raises(ValidationError, match="public coordinate pair"):
        location.full_clean()


def test_private_coordinates_are_never_reused_as_public_coordinates():
    location = make_location(
        visibility=Location.Visibility.AREA_ONLY,
        latitude_private=Decimal("10.676500"),
        longitude_private=Decimal("122.950900"),
    )
    location.full_clean()

    public = location.as_public_dict()

    assert "latitude" not in public
    assert "longitude" not in public


def test_property_type_rejects_arbitrary_applicable_fields():
    property_type = PropertyType(
        name="Invalid Type",
        slug="invalid-type",
        applicable_fields=["bedrooms", "arbitrary_column"],
    )

    with pytest.raises(ValidationError, match="Unsupported fields"):
        property_type.full_clean()


def test_property_type_name_is_case_insensitively_unique():
    make_property_type(name="Case Type", slug="case-type-one")

    with pytest.raises(IntegrityError), transaction.atomic():
        PropertyType.objects.bulk_create(
            [
                PropertyType(
                    name="CASE TYPE",
                    slug="case-type-two",
                    applicable_fields=[],
                )
            ]
        )


def test_inactive_property_type_cannot_be_assigned_to_new_variant():
    location = make_location()
    development = make_development(location)
    property_type = make_property_type(active=False)
    variant = Variant(
        development=development,
        property_type=property_type,
        name="Model A",
        slug="model-a",
        description="Description",
    )

    with pytest.raises(ValidationError, match="Inactive property types"):
        variant.full_clean()

    with pytest.raises(ValidationError, match="Inactive property types"):
        variant.save()


def test_property_variant_must_match_development_and_property_type():
    first_location = make_location()
    second_location = make_location(public_label="Talisay City", city_municipality="Talisay")
    first_development = make_development(first_location)
    second_development = make_development(
        second_location,
        name="Second Development",
        slug="second-development",
    )
    house_type = make_property_type()
    lot_type = make_property_type(name="Test Lot", slug="test-lot")
    variant = Variant.objects.create(
        development=first_development,
        property_type=house_type,
        name="Model B",
        slug="model-b",
        description="Description",
    )
    property_record = Property(
        development=second_development,
        variant=variant,
        property_type=lot_type,
        location=second_location,
        reference_code="PROP-001",
    )

    with pytest.raises(ValidationError) as error:
        property_record.full_clean()

    assert "variant" in error.value.message_dict
    assert "property_type" in error.value.message_dict


def test_standalone_property_does_not_require_development_or_variant():
    location = make_location()
    property_type = make_property_type()
    property_record = Property(
        location=location,
        property_type=property_type,
        reference_code="STANDALONE-001",
        title_override="Standalone Home",
    )

    property_record.full_clean()
    property_record.save()

    assert property_record.development is None
    assert property_record.variant is None


def test_hidden_location_returns_no_geographic_information():
    location = make_location(
        visibility=Location.Visibility.HIDDEN,
        street_address_private="123 Private Street",
    )

    assert location.as_public_dict() == {"visibility": Location.Visibility.HIDDEN}


def test_property_public_projection_excludes_internal_identifiers():
    location = make_location()
    property_type = make_property_type()
    property_record = Property.objects.create(
        location=location,
        property_type=property_type,
        reference_code="INTERNAL-SECRET-001",
        unit_or_lot_number_private="Lot 42",
    )

    public = property_record.as_public_dict()

    assert public["title"] == property_type.name
    assert "reference_code" not in public
    assert "unit_or_lot_number_private" not in public


def test_postgresql_rejects_out_of_range_coordinates_when_validation_is_bypassed():
    with pytest.raises(IntegrityError), transaction.atomic():
        Location.objects.bulk_create(
            [
                Location(
                    city_municipality="Bacolod",
                    public_label="Invalid coordinate",
                    latitude_private=Decimal("91"),
                    longitude_private=Decimal("122"),
                )
            ]
        )


def test_map_coordinate_widget_uses_hidden_storage_and_clickable_picker():
    widget = MapCoordinateWidget(map_name="public", axis="latitude")

    rendered = widget.render("public_latitude", Decimal("10.676500"), {"id": "id_public_latitude"})

    assert 'type="hidden"' in rendered
    assert 'data-map-picker="public"' in rendered
    assert "Click the map" in rendered


def test_location_admin_form_hides_private_fields_from_admin_but_not_owner():
    from django.contrib.auth import get_user_model

    from .forms import LocationAdminForm

    user_model = get_user_model()
    admin = user_model(
        username="location-admin", email="location-admin@example.test", role=user_model.Role.ADMIN
    )
    owner = user_model(
        username="location-owner", email="location-owner@example.test", role=user_model.Role.OWNER
    )

    admin_form = LocationAdminForm(for_user=admin)
    owner_form = LocationAdminForm(for_user=owner)

    assert "street_address_private" not in admin_form.fields
    assert "latitude_private" not in admin_form.fields
    assert "longitude_private" not in admin_form.fields
    assert "street_address_private" in owner_form.fields


def test_psgc_dataset_and_public_endpoint_include_full_hierarchy(client):
    from django.urls import reverse

    from .geography import psgc_data, validate_geography

    data = psgc_data()
    assert len(data["regions"]) == 18
    assert validate_geography("Negros Island Region (NIR)", "Negros Occidental", "City of Talisay")
    assert validate_geography("Negros Island Region (NIR)", "__independent__", "City of Bacolod")

    response = client.get(reverse("philippine_geography"))
    assert response.status_code == 200
    assert response.json()["version"] == "PSGC 2Q 2026"


def test_location_admin_form_rejects_mismatched_geography():
    from django.contrib.auth import get_user_model

    from .forms import LocationAdminForm

    user_model = get_user_model()
    owner = user_model(
        username="geo-owner", email="geo-owner@example.test", role=user_model.Role.OWNER
    )
    form = LocationAdminForm(
        data={
            "country_code": "PH",
            "region": "Negros Island Region (NIR)",
            "province": "Negros Occidental",
            "city_municipality": "City of Cebu",
            "public_label": "Invalid pairing",
            "visibility": Location.Visibility.AREA_ONLY,
        },
        for_user=owner,
    )

    assert not form.is_valid()
    assert "city_municipality" in form.errors


def test_unused_location_can_be_deleted_but_referenced_location_is_protected():
    unused = make_location(public_label="Unused location")
    unused_id = unused.pk
    unused.delete()
    assert not Location.objects.filter(pk=unused_id).exists()

    referenced = make_location(public_label="Referenced location")
    Development.objects.create(
        location=referenced,
        name="Protected development",
        slug="protected-development",
        development_type=Development.Type.SUBDIVISION,
        summary="Protected by its location relationship.",
        description="Protected development description.",
    )
    with pytest.raises(ProtectedError):
        referenced.delete()


def test_successful_location_deletion_is_audited_without_private_details():
    from types import SimpleNamespace

    from .wagtail_hooks import audit_location_deletions, capture_location_deletions

    user_model = get_user_model()
    owner = user_model.objects.create_user(
        username="delete-owner",
        email="delete-owner@example.test",
        password="safe-test-password",
        role=user_model.Role.OWNER,
        status=user_model.Status.ACTIVE,
    )
    location = make_location(
        public_label="Disposable location",
        street_address_private="Do not log this address",
    )
    location_id = str(location.pk)
    request = SimpleNamespace(user=owner)

    capture_location_deletions(request, [location])
    location.delete()
    audit_location_deletions(request, [location])

    event = AuditEvent.objects.get(action="catalogue.location.deleted", target_id=location_id)
    assert event.actor == owner
    assert event.metadata["public_label"] == "Disposable location"
    assert "street_address_private" not in event.metadata
