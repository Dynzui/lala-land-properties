import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from apps.audittrail.models import AuditEvent, CatalogRevision

from .models import Development, Location, Property, PropertyType, Variant
from .services import (
    archive_catalog_record,
    reactivate_catalog_record,
    record_catalog_change,
    restore_catalog_revision,
    serialize_catalog_record,
)

pytestmark = pytest.mark.django_db


def make_owner():
    user_model = get_user_model()
    return user_model.objects.create_user(
        username="catalogue-owner",
        email="catalogue-owner@example.test",
        password="safe-test-password",
        role=user_model.Role.OWNER,
        status=user_model.Status.ACTIVE,
    )


def make_catalogue():
    location = Location.objects.create(
        city_municipality="Bacolod",
        province="Negros Occidental",
        public_label="Bacolod City, Negros Occidental",
    )
    property_type = PropertyType.objects.create(
        name="Service Test House",
        slug="service-test-house",
        applicable_fields=["bedrooms"],
    )
    development = Development.objects.create(
        location=location,
        name="Service Development",
        slug="service-development",
        development_type=Development.Type.SUBDIVISION,
        summary="Service test.",
        description="Service test development.",
        status=Development.Status.ACTIVE,
    )
    return location, property_type, development


def test_catalogue_change_creates_audit_event_and_revision():
    owner = make_owner()
    _, _, development = make_catalogue()

    revision = record_catalog_change(
        actor=owner,
        record=development,
        action="catalogue.record.created",
    )

    assert revision.revision_number == 1
    assert CatalogRevision.objects.filter(entity_id=development.pk).count() == 1
    assert AuditEvent.objects.filter(
        action="catalogue.record.created",
        target_id=str(development.pk),
    ).exists()


def test_restoration_creates_a_new_revision_instead_of_overwriting_history():
    owner = make_owner()
    _, _, development = make_catalogue()
    first = record_catalog_change(
        actor=owner,
        record=development,
        action="catalogue.record.created",
    )
    development.summary = "Changed summary."
    before = serialize_catalog_record(development)
    development.save()
    record_catalog_change(
        actor=owner,
        record=development,
        action="catalogue.record.updated",
        before=before,
    )

    restore_catalog_revision(actor=owner, record=development, revision=first)

    development.refresh_from_db()
    assert development.summary == "Service test."
    assert list(
        CatalogRevision.objects.filter(entity_id=development.pk).values_list(
            "revision_number", flat=True
        )
    ) == [3, 2, 1]


def test_archive_and_reactivate_preserve_record_for_reuse():
    owner = make_owner()
    _, _, development = make_catalogue()

    archive_catalog_record(actor=owner, record=development, reason="Temporarily retired")
    assert development.status == Development.Status.ARCHIVED
    assert development.archived_at is not None

    reactivate_catalog_record(actor=owner, record=development)
    assert development.status == Development.Status.DRAFT
    assert development.archived_at is None
    assert Development.objects.filter(pk=development.pk).exists()


def test_development_archive_is_blocked_until_published_listings_are_archived():
    from apps.listings.models import Listing, Offer

    owner = make_owner()
    location, property_type, development = make_catalogue()
    variant = Variant.objects.create(
        development=development,
        property_type=property_type,
        name="Archive Guard Variant",
        slug="archive-guard-variant",
        description="Archive guard variant.",
        status=Variant.Status.ACTIVE,
    )
    property_record = Property.objects.create(
        development=development,
        variant=variant,
        property_type=property_type,
        location=location,
        reference_code="ARCHIVE-GUARD-001",
    )
    listing = Listing.objects.create(
        property=property_record,
        title="Archive Guard Listing",
        slug="archive-guard-listing",
        summary="Archive guard listing.",
        description="Archive guard listing.",
        inventory_mode=Listing.InventoryMode.SINGLE,
    )
    Offer.objects.create(
        listing=listing,
        transaction_type=Offer.TransactionType.SALE,
        price_display=Offer.PriceDisplay.EXACT,
        price_min=1000000,
    )
    listing.workflow_status = Listing.WorkflowStatus.PUBLISHED
    listing.save()

    with pytest.raises(ValidationError) as error:
        archive_catalog_record(actor=owner, record=development)

    message = error.value.message_dict["status"][0]
    assert "Archive Guard Listing" in message
    assert "Archive Guard Variant" in message
    assert "ARCHIVE-GUARD-001" in message
    development.refresh_from_db()
    variant.refresh_from_db()
    property_record.refresh_from_db()
    assert development.status == Development.Status.ACTIVE
    assert variant.status == Variant.Status.ACTIVE
    assert property_record.archived_at is None

    listing.workflow_status = Listing.WorkflowStatus.ARCHIVED
    listing.save()
    archive_catalog_record(actor=owner, record=development)

    development.refresh_from_db()
    variant.refresh_from_db()
    property_record.refresh_from_db()
    assert development.status == Development.Status.ARCHIVED
    assert variant.status == Variant.Status.ACTIVE
    assert property_record.archived_at is None


def test_archived_development_cannot_receive_active_variant_or_new_property():
    owner = make_owner()
    location, property_type, development = make_catalogue()
    archive_catalog_record(actor=owner, record=development)
    variant = Variant(
        development=development,
        property_type=property_type,
        name="Blocked Variant",
        slug="blocked-variant",
        description="Cannot activate.",
        status=Variant.Status.ACTIVE,
    )
    property_record = Property(
        development=development,
        property_type=property_type,
        location=location,
        reference_code="BLOCKED-001",
    )

    with pytest.raises(ValidationError, match="active development"):
        variant.save()
    with pytest.raises(ValidationError, match="archived development"):
        property_record.save()


def test_private_location_values_are_not_written_to_audit_metadata():
    owner = make_owner()
    location, _, _ = make_catalogue()
    location.street_address_private = "123 Secret Street"
    location.latitude_private = "10.123456"
    location.longitude_private = "122.123456"
    location.save()

    record_catalog_change(
        actor=owner,
        record=location,
        action="catalogue.record.updated",
    )

    metadata = AuditEvent.objects.get(target_id=str(location.pk)).metadata
    rendered = str(metadata)
    assert "Secret Street" not in rendered
    assert "latitude_private" not in rendered
    assert "longitude_private" not in rendered
