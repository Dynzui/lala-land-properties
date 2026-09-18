from decimal import Decimal
from urllib.parse import urlencode

from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.media_library.models import CatalogueMedia
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
    floor_plans = media_for_listing(listing, kind=CatalogueMedia.Kind.FLOOR_PLAN)
    active_offer = next((offer for offer in listing.offers.all() if offer.active), None)
    target = listing.property if listing.property_id else listing.variant
    candidates = list(
        Listing.objects.public()
        .exclude(pk=listing.pk)
        .select_related(
            "property__location",
            "property__property_type",
            "variant__development__location",
            "variant__property_type",
        )
        .prefetch_related("offers")
        .order_by("-featured", "-published_at")[:60]
    )
    current_location = (
        listing.property.location if listing.property_id else listing.variant.development.location
    )
    current_offer_price = active_offer.price_min if active_offer else None
    similar_listings = []
    for candidate in candidates:
        candidate_target = candidate.property if candidate.property_id else candidate.variant
        candidate_location = (
            candidate.property.location
            if candidate.property_id
            else candidate.variant.development.location
        )
        candidate_offer = next((offer for offer in candidate.offers.all() if offer.active), None)
        score = 0
        if candidate_target.property_type_id == target.property_type_id:
            score += 5
        if candidate_location.city_municipality == current_location.city_municipality:
            score += 4
        elif candidate_location.province == current_location.province:
            score += 2
        if candidate_target.bedrooms is not None and target.bedrooms is not None:
            score += max(0, 2 - abs(candidate_target.bedrooms - target.bedrooms))
        if current_offer_price and candidate_offer and candidate_offer.price_min:
            ratio = candidate_offer.price_min / current_offer_price
            if Decimal("0.7") <= ratio <= Decimal("1.3"):
                score += 2
        candidate.card_media = next(iter(media_for_listing(candidate)), None)
        candidate.active_offer = candidate_offer
        candidate.property_type_label = candidate_target.property_type.name
        candidate.bedrooms_label = candidate_target.bedrooms
        similar_listings.append((score, candidate))
    similar_listings = [
        candidate
        for _, candidate in sorted(
            similar_listings,
            key=lambda item: (item[0], item[1].featured, item[1].published_at),
            reverse=True,
        )[:6]
    ]
    return render(
        request,
        "listings/listing_detail.html",
        {
            "listing": listing,
            "public_listing": listing.as_public_dict(),
            "gallery": gallery,
            "cover_media": next(iter(gallery), None),
            "floor_plans": floor_plans,
            "active_offer": active_offer,
            "property_target": target,
            "similar_listings": similar_listings,
        },
    )


def listing_inquiry(request, listing_id):
    listing = get_object_or_404(Listing.objects.public(), pk=listing_id)
    query = urlencode({"listing": str(listing.pk), "property": listing.title})
    return redirect(f"{reverse('inquiries:contact')}?{query}")
