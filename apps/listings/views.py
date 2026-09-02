from urllib.parse import urlencode

from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.media_library.services import media_for_listing
from apps.properties.geography import INDEPENDENT

from .forms import ListingFilterForm
from .models import Listing


def listing_index(request):
    form = ListingFilterForm(request.GET or None)
    listings = (
        Listing.objects.public()
        .select_related(
            "property__location",
            "property__property_type",
            "variant__development__location",
            "variant__property_type",
        )
        .prefetch_related("offers")
    )
    if form.is_valid():
        filters = form.cleaned_data
        if filters["transaction"]:
            listings = listings.filter(
                offers__active=True, offers__transaction_type=filters["transaction"]
            )
        if filters["property_type"]:
            listings = listings.filter(
                Q(property__property_type=filters["property_type"])
                | Q(variant__property_type=filters["property_type"])
            )
        if filters["region"]:
            listings = listings.filter(
                Q(property__location__region=filters["region"])
                | Q(variant__development__location__region=filters["region"])
            )
        if filters["province"]:
            province = "" if filters["province"] == INDEPENDENT else filters["province"]
            listings = listings.filter(
                Q(property__location__province=province)
                | Q(variant__development__location__province=province)
            )
        if filters["city_municipality"]:
            listings = listings.filter(
                Q(property__location__city_municipality=filters["city_municipality"])
                | Q(variant__development__location__city_municipality=filters["city_municipality"])
            )
        if filters["bedrooms"]:
            bedrooms = int(filters["bedrooms"])
            listings = listings.filter(
                Q(property__bedrooms__gte=bedrooms) | Q(variant__bedrooms__gte=bedrooms)
            )
        if filters["min_price"] is not None:
            listings = listings.filter(
                offers__active=True, offers__price_min__gte=filters["min_price"]
            )
        if filters["max_price"] is not None:
            listings = listings.filter(
                offers__active=True, offers__price_min__lte=filters["max_price"]
            )
        if filters["status"]:
            listings = listings.filter(public_status=filters["status"])
    listings = listings.distinct()
    for listing in listings:
        listing.card_media = next(iter(media_for_listing(listing)), None)
        listing.active_offer = next((offer for offer in listing.offers.all() if offer.active), None)
        target = listing.property if listing.property_id else listing.variant
        listing.property_type_label = target.property_type.name
        listing.bedrooms_label = target.bedrooms
    return render(
        request,
        "listings/listing_index.html",
        {"listings": listings, "filter_form": form, "has_filters": bool(request.GET)},
    )


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
    active_offer = next((offer for offer in listing.offers.all() if offer.active), None)
    target = listing.property if listing.property_id else listing.variant
    return render(
        request,
        "listings/listing_detail.html",
        {
            "listing": listing,
            "public_listing": listing.as_public_dict(),
            "gallery": gallery,
            "cover_media": next(iter(gallery), None),
            "active_offer": active_offer,
            "property_target": target,
        },
    )


def listing_inquiry(request, listing_id):
    listing = get_object_or_404(Listing.objects.public(), pk=listing_id)
    query = urlencode({"listing": str(listing.pk), "property": listing.title})
    return redirect(f"{reverse('inquiries:contact')}?{query}")
