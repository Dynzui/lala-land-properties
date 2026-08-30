from urllib.parse import urlencode

from django.shortcuts import get_object_or_404, redirect, render

from apps.media_library.services import media_for_listing

from .models import Listing


def listing_index(request):
    listings = (
        Listing.objects.public()
        .select_related("property__location", "variant__development__location")
        .prefetch_related("offers")
    )
    for listing in listings:
        listing.card_media = next(iter(media_for_listing(listing)), None)
    return render(request, "listings/listing_index.html", {"listings": listings})


def listing_detail(request, slug):
    listing = get_object_or_404(
        Listing.objects.select_related(
            "property__location",
            "property__property_type",
            "variant__development__location",
            "variant__property_type",
        ).prefetch_related("offers"),
        slug=slug,
    )
    if not listing.is_publicly_available:
        return render(
            request,
            "listings/listing_unavailable.html",
            {"listing": listing},
            status=200,
        )
    gallery = media_for_listing(listing)
    return render(
        request,
        "listings/listing_detail.html",
        {
            "listing": listing,
            "public_listing": listing.as_public_dict(),
            "gallery": gallery,
            "cover_media": next(iter(gallery), None),
        },
    )


def listing_inquiry(request, listing_id):
    listing = get_object_or_404(Listing.objects.public(), pk=listing_id)
    query = urlencode({"listing": str(listing.pk), "property": listing.title})
    return redirect(f"/contact/?{query}")
