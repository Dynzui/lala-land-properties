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
