from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.urls import reverse

from apps.audittrail.models import AuditEvent
from apps.properties.models import Development, Location, Property, PropertyType, Variant

from .models import Listing, Offer
from .admin_forms import GuidedListingForm
from .services import archive_listing, publish_listing, restore_listing, set_public_status

pytestmark = pytest.mark.django_db


def make_owner():
    user_model = get_user_model()
    return user_model.objects.create_user(
        username="listing-owner",
        email="listing-owner@example.test",
        password="safe-test-password",
        role=user_model.Role.OWNER,
        status=user_model.Status.ACTIVE,
    )


def make_catalogue(*, hidden=False):
    location = Location.objects.create(
        region="Negros Island Region (NIR)",
        city_municipality="City of Bacolod",
        province="",
        public_label="Bacolod City, Negros Occidental",
        visibility=Location.Visibility.HIDDEN if hidden else Location.Visibility.AREA_ONLY,
    )
    property_type = PropertyType.objects.create(
        name="Listing Test House",
        slug="listing-test-house",
        applicable_fields=["bedrooms"],
    )
    development = Development.objects.create(
        location=location,
        name="Listing Test Development",
        slug="listing-test-development",
        development_type=Development.Type.SUBDIVISION,
        summary="Development summary.",
        description="Development description.",
        status=Development.Status.ACTIVE,
    )
    variant = Variant.objects.create(
        development=development,
        property_type=property_type,
        name="Model A",
        slug="model-a-listing-test",
        description="Variant description.",
        status=Variant.Status.ACTIVE,
    )
    property_record = Property.objects.create(
        development=development,
        variant=variant,
        location=location,
        property_type=property_type,
        reference_code="LISTING-PROP-001",
    )
    return location, variant, property_record


def make_listing(*, property_record=None, variant=None, pooled=False):
    return Listing.objects.create(
        property=property_record if not pooled else None,
        variant=variant if pooled else None,
        slug="test-listing",
        title="A Test Home",
        summary="A clear listing summary.",
        description="A complete listing description.",
        inventory_mode=Listing.InventoryMode.POOLED if pooled else Listing.InventoryMode.SINGLE,
        available_quantity=3 if pooled else None,
    )


def make_offer(listing, **overrides):
    values = {
        "listing": listing,
        "transaction_type": Offer.TransactionType.SALE,
        "price_display": Offer.PriceDisplay.EXACT,
        "price_min": Decimal("3500000"),
    }
    values.update(overrides)
    return Offer.objects.create(**values)


def test_listing_requires_exactly_one_matching_target():
    _, variant, property_record = make_catalogue()
    listing = Listing(
        property=property_record,
        variant=variant,
        slug="invalid-targets",
        title="Invalid",
        summary="Summary",
        description="Description",
        inventory_mode=Listing.InventoryMode.SINGLE,
    )

    with pytest.raises(ValidationError):
        listing.save()


def guided_listing_data(location_record, property_type_record, **overrides):
    values = {
        "title": "Guided Bacolod Home",
        "summary": "A home created in one clear workflow.",
        "description": "A complete customer-facing description.",
        "arrangement": Listing.InventoryMode.SINGLE,
        "development": "",
        "house_model": "",
        "available_quantity": "",
        "property_type": str(property_type_record.pk),
        "location": str(location_record.pk),
        "bedrooms": "3",
        "bathrooms": "2",
        "parking_spaces": "1",
        "floor_area_sqm": "110",
        "lot_area_sqm": "140",
        "furnishing": Property.Furnishing.UNFURNISHED,
        "transaction_type": Offer.TransactionType.SALE,
        "price_display": Offer.PriceDisplay.EXACT,
        "price_min": "4200000",
        "price_max": "",
        "rent_period": "",
        "public_status": Listing.PublicStatus.AVAILABLE,
        "featured": "",
    }
    values.update(overrides)
    return values


def test_guided_form_creates_property_listing_and_price_together():
    location, _, property_record = make_catalogue()
    owner = make_owner()
    form = GuidedListingForm(data=guided_listing_data(location, property_record.property_type))

    assert form.is_valid(), form.errors
    listing = form.save(actor=owner)

    assert listing.property.location == location
    assert listing.workflow_status == Listing.WorkflowStatus.DRAFT
    assert listing.offers.get().price_min == Decimal("4200000")
    assert AuditEvent.objects.filter(target_id=str(listing.pk)).exists()
    assert AuditEvent.objects.filter(target_id=str(listing.property_id)).exists()


def test_guided_form_creates_pooled_listing_without_property_step():
    location, variant, property_record = make_catalogue()
    owner = make_owner()
    data = guided_listing_data(
        location,
        property_record.property_type,
        title="Guided Model A",
        arrangement=Listing.InventoryMode.POOLED,
        house_model=str(variant.pk),
        available_quantity="4",
        property_type="",
        location="",
    )
    form = GuidedListingForm(data=data)

    assert form.is_valid(), form.errors
    listing = form.save(actor=owner)

    assert listing.variant == variant
    assert listing.property is None
    assert listing.available_quantity == 4


def test_guided_form_updates_listing_property_and_price_without_new_records():
    location, _, property_record = make_catalogue()
    owner = make_owner()
    listing = make_listing(property_record=property_record)
    offer = make_offer(listing)
    data = guided_listing_data(
        location,
        property_record.property_type,
        title="Updated Guided Home",
        bedrooms="4",
        price_min="5100000",
    )
    form = GuidedListingForm(data=data, listing=listing)

    assert form.is_valid(), form.errors
    updated = form.save(actor=owner)

    property_record.refresh_from_db()
    offer.refresh_from_db()
    assert updated.pk == listing.pk
    assert Property.objects.filter(pk=property_record.pk).count() == 1
    assert updated.title == "Updated Guided Home"
    assert property_record.bedrooms == 4
    assert offer.price_min == Decimal("5100000")


def test_pooled_listing_explains_required_variant_and_quantity():
    listing = Listing(
        slug="missing-pooled-target",
        title="Missing pooled target",
        summary="Summary",
        description="Description",
        inventory_mode=Listing.InventoryMode.POOLED,
    )

    with pytest.raises(ValidationError) as error:
        listing.full_clean()

    assert error.value.message_dict["variant"] == [
        "Choose the development variant represented by this listing."
    ]
    assert error.value.message_dict["available_quantity"] == [
        "Enter how many units of this variant are available."
    ]


def test_single_listing_explains_required_property():
    listing = Listing(
        slug="missing-single-target",
        title="Missing single target",
        summary="Summary",
        description="Description",
        inventory_mode=Listing.InventoryMode.SINGLE,
    )

    with pytest.raises(ValidationError) as error:
        listing.full_clean()

    assert error.value.message_dict["property"] == [
        "Choose the individual property represented by this listing."
    ]


def test_pooled_quantity_is_never_exposed_publicly():
    _, variant, _ = make_catalogue()
    listing = make_listing(variant=variant, pooled=True)
    make_offer(listing)
    owner = make_owner()
    listing = publish_listing(actor=owner, listing=listing)

    public = listing.as_public_dict()

    assert listing.available_quantity == 3
    assert "available_quantity" not in public


def test_only_one_active_offer_is_allowed_per_listing():
    _, _, property_record = make_catalogue()
    listing = make_listing(property_record=property_record)
    make_offer(listing)

    with pytest.raises(IntegrityError), transaction.atomic():
        Offer.objects.bulk_create(
            [
                Offer(
                    listing=listing,
                    transaction_type=Offer.TransactionType.RENT,
                    price_display=Offer.PriceDisplay.EXACT,
                    price_min=Decimal("25000"),
                    rent_period=Offer.RentPeriod.MONTHLY,
                )
            ]
        )


def test_rental_offer_requires_rent_period():
    _, _, property_record = make_catalogue()
    listing = make_listing(property_record=property_record)
    offer = Offer(
        listing=listing,
        transaction_type=Offer.TransactionType.RENT,
        price_display=Offer.PriceDisplay.EXACT,
        price_min=Decimal("25000"),
    )

    with pytest.raises(ValidationError, match="rent period"):
        offer.save()


def test_hidden_location_blocks_publication():
    _, _, property_record = make_catalogue(hidden=True)
    listing = make_listing(property_record=property_record)
    make_offer(listing)
    owner = make_owner()

    with pytest.raises(ValidationError, match="public-safe location"):
        publish_listing(actor=owner, listing=listing)


def test_direct_status_edit_cannot_bypass_publication_rules():
    _, _, property_record = make_catalogue()
    listing = make_listing(property_record=property_record)
    listing.workflow_status = Listing.WorkflowStatus.PUBLISHED

    with pytest.raises(ValidationError, match="active offer"):
        listing.save()


def test_offer_rejects_negative_fees_and_normalizes_currency():
    _, _, property_record = make_catalogue()
    listing = make_listing(property_record=property_record)
    offer = Offer(
        listing=listing,
        transaction_type=Offer.TransactionType.SALE,
        price_display=Offer.PriceDisplay.EXACT,
        price_min=Decimal("3500000"),
        reservation_fee=Decimal("-1"),
        currency="php",
    )

    with pytest.raises(ValidationError):
        offer.save()
    assert offer.currency == "PHP"


def test_publish_archive_and_status_changes_are_audited():
    _, _, property_record = make_catalogue()
    listing = make_listing(property_record=property_record)
    make_offer(listing)
    owner = make_owner()

    listing = publish_listing(actor=owner, listing=listing)
    assert listing.workflow_status == Listing.WorkflowStatus.PUBLISHED
    assert Listing.objects.public().filter(pk=listing.pk).exists()

    listing = set_public_status(
        actor=owner,
        listing=listing,
        status=Listing.PublicStatus.SOLD,
    )
    assert not Listing.objects.public().filter(pk=listing.pk).exists()

    listing = archive_listing(actor=owner, listing=listing)
    assert listing.workflow_status == Listing.WorkflowStatus.ARCHIVED
    assert AuditEvent.objects.filter(target_id=str(listing.pk)).count() == 3


def test_saved_url_shows_unavailable_page_for_sold_listing(client):
    _, _, property_record = make_catalogue()
    listing = make_listing(property_record=property_record)
    make_offer(listing)
    owner = make_owner()
    listing = publish_listing(actor=owner, listing=listing)
    listing = set_public_status(
        actor=owner,
        listing=listing,
        status=Listing.PublicStatus.SOLD,
    )

    response = client.get(reverse("listings:detail", args=[listing.slug]))

    assert response.status_code == 200
    assert "currently unavailable" in response.content.decode()


def test_public_index_excludes_unavailable_listings(client):
    _, _, property_record = make_catalogue()
    listing = make_listing(property_record=property_record)

    response = client.get(reverse("listings:index"))

    assert response.status_code == 200
    assert listing.title not in response.content.decode()


def test_public_index_includes_mobile_filter_controls(client):
    response = client.get(reverse("listings:index"))

    content = response.content.decode()
    assert response.status_code == 200
    assert 'id="property-filter"' in content
    assert 'class="mobile-filter-fab"' in content
    assert 'aria-label="Open property filters"' in content
    assert 'aria-controls="property-filter"' in content
    assert '<svg aria-hidden="true"' in content
    assert "</span> Filters</button>" not in content
    assert 'class="filter-close"' in content
    assert 'class="advanced-filters"' in content
    assert "Advanced filters" in content


def test_inquiry_link_tags_listing_and_routes_to_contact(client):
    _, _, property_record = make_catalogue()
    listing = make_listing(property_record=property_record)
    make_offer(listing)
    listing = publish_listing(actor=make_owner(), listing=listing)

    response = client.get(reverse("listings:inquiry", args=[listing.pk]))

    assert response.status_code == 302
    assert response.url.startswith("/contact/?")
    assert str(listing.pk) in response.url


def test_detail_recommends_only_other_public_listings(client):
    _, variant, property_record = make_catalogue()
    current = make_listing(property_record=property_record)
    make_offer(current)
    owner = make_owner()
    current = publish_listing(actor=owner, listing=current)
    similar = Listing.objects.create(
        variant=variant,
        slug="similar-home",
        title="Similar Home",
        summary="Another suitable home.",
        description="A second complete listing description.",
        inventory_mode=Listing.InventoryMode.POOLED,
        available_quantity=2,
    )
    make_offer(similar)
    similar = publish_listing(actor=owner, listing=similar)
    unavailable = Listing.objects.create(
        variant=variant,
        slug="hidden-home",
        title="Hidden Home",
        summary="This should not be recommended.",
        description="An unavailable listing description.",
        inventory_mode=Listing.InventoryMode.POOLED,
        available_quantity=1,
    )
    make_offer(unavailable)

    response = client.get(reverse("listings:detail", args=[current.slug]))

    assert response.status_code == 200
    assert similar in response.context["similar_listings"]
    assert unavailable not in response.context["similar_listings"]
    assert current not in response.context["similar_listings"]


def test_public_property_search_filters_sale_location_type_bedrooms_and_price(client):
    location, _, property_record = make_catalogue()
    property_record.bedrooms = 3
    property_record.save()
    listing = make_listing(property_record=property_record)
    make_offer(listing, price_min=Decimal("3500000"))
    listing = publish_listing(actor=make_owner(), listing=listing)

    response = client.get(
        reverse("listings:index"),
        {
            "transaction": "SALE",
            "property_type": property_record.property_type.slug,
            "region": "Negros Island Region (NIR)",
            "province": "__independent__",
            "city_municipality": "City of Bacolod",
            "bedrooms": "3",
            "min_price": "3000000",
            "max_price": "4000000",
        },
    )

    content = response.content.decode()
    assert response.status_code == 200
    assert listing.title in content
    assert "₱3,500,000" in content


def test_public_property_search_rejects_reversed_price_range(client):
    response = client.get(
        reverse("listings:index"),
        {"min_price": "5000000", "max_price": "1000000"},
    )

    assert response.status_code == 200
    assert "Please check the price range" in response.content.decode()


def test_offer_formats_php_rental_and_range_prices():
    _, _, property_record = make_catalogue()
    rental_listing = make_listing(property_record=property_record)
    rental = make_offer(
        rental_listing,
        transaction_type=Offer.TransactionType.RENT,
        price_min=Decimal("25000"),
        rent_period=Offer.RentPeriod.MONTHLY,
    )
    assert rental.display_price == "₱25,000 / monthly"

    rental.active = False
    rental.save()
    price_range = Offer.objects.create(
        listing=rental_listing,
        transaction_type=Offer.TransactionType.SALE,
        price_display=Offer.PriceDisplay.RANGE,
        price_min=Decimal("3000000"),
        price_max=Decimal("4500000"),
    )
    assert price_range.display_price == "₱3,000,000–₱4,500,000"


def test_archived_listing_can_be_restored_as_audited_draft():
    _, _, property_record = make_catalogue()
    owner = make_owner()
    listing = make_listing(property_record=property_record)
    make_offer(listing)
    listing = publish_listing(actor=owner, listing=listing)
    listing = archive_listing(actor=owner, listing=listing)

    restored = restore_listing(actor=owner, listing=listing)

    assert restored.workflow_status == Listing.WorkflowStatus.DRAFT
    assert restored.archived_at is None
    assert AuditEvent.objects.filter(action="listing.restored", target_id=str(listing.pk)).exists()
