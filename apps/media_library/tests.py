import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse
from wagtail.images import get_image_model
from wagtail.images.tests.utils import get_test_image_file

from apps.listings.services import publish_listing
from apps.listings.tests import make_catalogue, make_listing, make_offer, make_owner

from .models import CatalogueMedia
from .services import media_for_listing

pytestmark = pytest.mark.django_db


def make_image(title="Property photo"):
    image_model = get_image_model()
    return image_model.objects.create(
        title=title,
        file=get_test_image_file(filename=f"{title.lower().replace(' ', '-')}.png"),
    )


def test_media_requires_exactly_one_target_and_alt_text():
    media = CatalogueMedia(image=make_image(), alt_text="Front of the home")
    with pytest.raises(ValidationError, match="exactly one"):
        media.save()

    _, variant, property_record = make_catalogue()
    media.property = property_record
    media.variant = variant
    with pytest.raises(ValidationError, match="exactly one"):
        media.save()

    media.variant = None
    media.alt_text = ""
    with pytest.raises(ValidationError, match="Alternative text"):
        media.save()


def test_new_cover_demotes_previous_cover_for_same_target():
    _, _, property_record = make_catalogue()
    first = CatalogueMedia.objects.create(
        image=make_image("First"),
        property=property_record,
        alt_text="Front elevation",
        is_cover=True,
    )
    second = CatalogueMedia.objects.create(
        image=make_image("Second"),
        property=property_record,
        alt_text="Garden view",
        is_cover=True,
    )

    first.refresh_from_db()
    assert first.is_cover is False
    assert second.is_cover is True


def test_floor_plan_cannot_be_used_as_cover():
    _, _, property_record = make_catalogue()
    floor_plan = CatalogueMedia(
        image=make_image("Floor plan"),
        property=property_record,
        kind=CatalogueMedia.Kind.FLOOR_PLAN,
        alt_text="Ground floor layout",
        is_cover=True,
    )

    with pytest.raises(ValidationError, match="Only a property photo"):
        floor_plan.save()


def test_media_inheritance_prefers_property_then_variant_then_development():
    _, variant, property_record = make_catalogue()
    listing = make_listing(property_record=property_record)
    development_media = CatalogueMedia.objects.create(
        image=make_image("Development"),
        development=variant.development,
        alt_text="Development entrance",
    )
    variant_media = CatalogueMedia.objects.create(
        image=make_image("Variant"),
        variant=variant,
        alt_text="Model home",
    )

    assert media_for_listing(listing) == [variant_media]

    property_media = CatalogueMedia.objects.create(
        image=make_image("Property"),
        property=property_record,
        alt_text="Exact property",
    )
    assert media_for_listing(listing) == [property_media]

    property_media.archive()
    variant_media.archive()
    assert media_for_listing(listing) == [development_media]


def test_public_pages_render_managed_image_and_alt_text(client):
    _, _, property_record = make_catalogue()
    listing = make_listing(property_record=property_record)
    make_offer(listing)
    listing = publish_listing(actor=make_owner(), listing=listing)
    CatalogueMedia.objects.create(
        image=make_image("Public property"),
        property=property_record,
        alt_text="Ivory home with a landscaped front garden",
        is_cover=True,
    )

    index_response = client.get(reverse("listings:index"))
    detail_response = client.get(reverse("listings:detail", args=[listing.slug]))

    assert index_response.status_code == 200
    assert detail_response.status_code == 200
    assert b"Ivory home with a landscaped front garden" in index_response.content
    assert b"Ivory home with a landscaped front garden" in detail_response.content


def test_detail_separates_floor_plans_from_photo_gallery(client):
    _, _, property_record = make_catalogue()
    listing = make_listing(property_record=property_record)
    make_offer(listing)
    listing = publish_listing(actor=make_owner(), listing=listing)
    photo = CatalogueMedia.objects.create(
        image=make_image("Exterior"), property=property_record, alt_text="Home exterior"
    )
    floor_plan = CatalogueMedia.objects.create(
        image=make_image("Plan"),
        property=property_record,
        kind=CatalogueMedia.Kind.FLOOR_PLAN,
        alt_text="Two bedroom floor plan",
    )

    response = client.get(reverse("listings:detail", args=[listing.slug]))

    assert response.context["gallery"] == [photo]
    assert response.context["floor_plans"] == [floor_plan]
    assert b"Property gallery" in response.content
    assert b"Floor plan" in response.content
