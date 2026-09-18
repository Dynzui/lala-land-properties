from uuid import uuid4

from django import forms
from django.db import transaction
from django.utils.html import strip_tags
from django.utils.text import slugify

from apps.properties.models import Development, Location, Property, PropertyType, Variant
from apps.properties.services import record_catalog_change, serialize_catalog_record

from .models import Listing, Offer
from .services import record_listing_change, serialize_record


class GuidedListingForm(forms.Form):
    """A plain-language facade over the normalized catalogue models."""

    title = forms.CharField(max_length=180, help_text="The name customers will see.")
    summary = forms.CharField(
        max_length=300,
        widget=forms.Textarea(attrs={"rows": 2}),
        help_text="A short introduction shown on property cards.",
    )
    description = forms.CharField(widget=forms.Textarea(attrs={"rows": 6}))

    arrangement = forms.ChoiceField(
        choices=[
            (Listing.InventoryMode.SINGLE, "One specific property or lot"),
            (Listing.InventoryMode.POOLED, "Several interchangeable units of one house model"),
        ],
        widget=forms.RadioSelect,
        help_text="Most resale homes, rentals, and individual lots use one specific property.",
    )
    development = forms.ModelChoiceField(
        queryset=Development.objects.none(),
        required=False,
        empty_label="Not part of a development",
        help_text=(
            "Optional for a specific property. The house model already determines this "
            "for pooled inventory."
        ),
    )
    house_model = forms.ModelChoiceField(
        queryset=Variant.objects.none(),
        required=False,
        empty_label="No house model",
        label="House model",
        help_text="Required only when one listing represents several interchangeable units.",
    )
    available_quantity = forms.IntegerField(
        required=False,
        min_value=1,
        label="Number of units available",
    )

    property_type = forms.ModelChoiceField(
        queryset=PropertyType.objects.none(),
        required=False,
        help_text="For pooled inventory, this comes from the selected house model.",
    )
    location = forms.ModelChoiceField(
        queryset=Location.objects.none(),
        required=False,
        help_text="For pooled inventory, this comes from the selected development.",
    )
    bedrooms = forms.IntegerField(required=False, min_value=0)
    bathrooms = forms.DecimalField(required=False, min_value=0, max_digits=4, decimal_places=1)
    parking_spaces = forms.IntegerField(required=False, min_value=0)
    floor_area_sqm = forms.DecimalField(
        required=False, min_value=0, max_digits=12, decimal_places=2
    )
    lot_area_sqm = forms.DecimalField(required=False, min_value=0, max_digits=12, decimal_places=2)
    furnishing = forms.ChoiceField(
        required=False, choices=[("", "Not specified"), *Property.Furnishing.choices]
    )

    transaction_type = forms.ChoiceField(
        choices=Offer.TransactionType.choices, label="For sale or rent"
    )
    price_display = forms.ChoiceField(
        choices=Offer.PriceDisplay.choices, label="How to show the price"
    )
    price_min = forms.DecimalField(
        required=False, min_value=1, max_digits=14, decimal_places=2, label="Price"
    )
    price_max = forms.DecimalField(
        required=False, min_value=1, max_digits=14, decimal_places=2, label="Maximum price"
    )
    rent_period = forms.ChoiceField(
        required=False, choices=[("", "Select a rental period"), *Offer.RentPeriod.choices]
    )
    public_status = forms.ChoiceField(
        choices=Listing.PublicStatus.choices, initial=Listing.PublicStatus.AVAILABLE
    )
    featured = forms.BooleanField(
        required=False, help_text="Show this listing more prominently on the website."
    )

    def __init__(self, *args, listing=None, **kwargs):
        self.listing = listing
        super().__init__(*args, **kwargs)
        self.fields["development"].queryset = Development.objects.exclude(
            status=Development.Status.ARCHIVED
        ).order_by("name")
        self.fields["house_model"].queryset = Variant.objects.filter(
            status=Variant.Status.ACTIVE,
            archived_at__isnull=True,
            development__status=Development.Status.ACTIVE,
            development__archived_at__isnull=True,
        ).select_related("development", "property_type")
        self.fields["property_type"].queryset = PropertyType.objects.filter(active=True)
        self.fields["location"].queryset = Location.objects.exclude(
            visibility=Location.Visibility.HIDDEN
        ).order_by("province", "city_municipality", "public_label")
        for name in ("price_min", "price_max"):
            self.fields[name].widget.attrs.update({"step": "1000", "inputmode": "numeric"})
        if listing is not None:
            target = listing.property if listing.property_id else listing.variant
            offer = listing.offers.filter(active=True).first() or listing.offers.first()
            initial = {
                "title": listing.title,
                "summary": listing.summary,
                "description": strip_tags(str(listing.description)),
                "arrangement": listing.inventory_mode,
                "development": (
                    listing.property.development_id
                    if listing.property_id
                    else listing.variant.development_id
                ),
                "house_model": (
                    listing.property.variant_id if listing.property_id else listing.variant_id
                ),
                "available_quantity": listing.available_quantity,
                "property_type": target.property_type_id,
                "location": listing.property.location_id if listing.property_id else None,
                "bedrooms": target.bedrooms,
                "bathrooms": target.bathrooms,
                "parking_spaces": getattr(target, "parking_spaces", None),
                "floor_area_sqm": target.floor_area_sqm,
                "lot_area_sqm": target.lot_area_sqm,
                "furnishing": getattr(target, "furnishing", ""),
                "public_status": listing.public_status,
                "featured": listing.featured,
            }
            if offer:
                initial.update(
                    transaction_type=offer.transaction_type,
                    price_display=offer.price_display,
                    price_min=offer.price_min,
                    price_max=offer.price_max,
                    rent_period=offer.rent_period,
                )
            self.initial.update(initial)
            self.fields["arrangement"].disabled = True
            self.fields[
                "arrangement"
            ].help_text = "This choice is locked after creation to preserve inventory history."

    def clean(self):
        cleaned = super().clean()
        arrangement = cleaned.get("arrangement")
        model = cleaned.get("house_model")
        development = cleaned.get("development")

        if arrangement == Listing.InventoryMode.POOLED:
            if not model:
                self.add_error("house_model", "Choose the house model shared by these units.")
            if cleaned.get("available_quantity") is None:
                self.add_error(
                    "available_quantity", "Enter how many units are currently available."
                )
        else:
            if not cleaned.get("property_type"):
                self.add_error("property_type", "Choose the type of this property.")
            if not cleaned.get("location"):
                self.add_error("location", "Choose where this property is located.")
            if model and development and model.development_id != development.id:
                self.add_error("house_model", "Choose a house model from the selected development.")
            if model and not development:
                cleaned["development"] = model.development
            if (
                model
                and cleaned.get("property_type")
                and model.property_type_id != cleaned["property_type"].id
            ):
                self.add_error(
                    "property_type", "Property type must match the selected house model."
                )

        price_display = cleaned.get("price_display")
        price_min = cleaned.get("price_min")
        price_max = cleaned.get("price_max")
        if price_display in {Offer.PriceDisplay.EXACT, Offer.PriceDisplay.STARTING_AT}:
            if price_min is None:
                self.add_error("price_min", "Enter the price to display.")
            if price_max is not None:
                self.add_error("price_max", "Leave maximum price empty for this price format.")
        elif price_display == Offer.PriceDisplay.RANGE:
            if price_min is None:
                self.add_error("price_min", "Enter the minimum price.")
            if price_max is None:
                self.add_error("price_max", "Enter the maximum price.")
            elif price_min is not None and price_max < price_min:
                self.add_error("price_max", "Maximum price must be at least the minimum price.")
        elif price_display == Offer.PriceDisplay.CONTACT and (price_min or price_max):
            self.add_error("price_min", "Leave prices empty when customers should contact Lala.")

        if cleaned.get("transaction_type") == Offer.TransactionType.RENT:
            if not cleaned.get("rent_period"):
                self.add_error("rent_period", "Choose how often rent is charged.")
        elif cleaned.get("rent_period"):
            self.add_error("rent_period", "Rental period only applies to rental listings.")
        return cleaned

    @transaction.atomic
    def save(self, *, actor):
        data = self.cleaned_data
        arrangement = data["arrangement"]
        property_record = None
        variant = None
        if arrangement == Listing.InventoryMode.POOLED:
            variant = data["house_model"]
        else:
            model = data.get("house_model")
            property_record = (
                self.listing.property
                if self.listing
                else Property(
                    reference_code=f"LLP-{uuid4().hex[:8].upper()}",
                    inventory_status=Property.InventoryStatus.AVAILABLE,
                )
            )
            property_before = serialize_catalog_record(property_record) if self.listing else None
            property_record.development = data.get("development")
            property_record.variant = model
            property_record.location = data["location"]
            property_record.property_type = data["property_type"]
            property_record.title_override = data["title"]
            property_record.bedrooms = data.get("bedrooms")
            property_record.bathrooms = data.get("bathrooms")
            property_record.parking_spaces = data.get("parking_spaces")
            property_record.floor_area_sqm = data.get("floor_area_sqm")
            property_record.lot_area_sqm = data.get("lot_area_sqm")
            property_record.furnishing = data.get("furnishing") or ""
            property_record.save()
            record_catalog_change(
                actor=actor,
                record=property_record,
                action=(
                    "catalogue.property.updated" if self.listing else "catalogue.property.created"
                ),
                before=property_before,
                change_summary=("Updated" if self.listing else "Created")
                + " through the guided listing form",
            )

        listing = self.listing or Listing(workflow_status=Listing.WorkflowStatus.DRAFT)
        listing_before = serialize_record(listing) if self.listing else None
        if not self.listing:
            slug_root = slugify(data["title"])[:190] or "property"
            listing.slug = (
                slug_root
                if not Listing.objects.filter(slug=slug_root).exists()
                else f"{slug_root}-{uuid4().hex[:6]}"
            )
        listing.property = property_record
        listing.variant = variant
        listing.title = data["title"]
        listing.summary = data["summary"]
        listing.description = data["description"]
        listing.inventory_mode = arrangement
        listing.available_quantity = data.get("available_quantity") if variant else None
        listing.public_status = data["public_status"]
        listing.featured = data.get("featured", False)
        listing.save()
        record_listing_change(
            actor=actor,
            record=listing,
            action="listing.record.updated" if self.listing else "listing.record.created",
            before=listing_before,
        )
        offer = listing.offers.filter(active=True).first() or listing.offers.first()
        offer_before = serialize_record(offer) if offer else None
        offer = offer or Offer(listing=listing, currency="PHP", active=True)
        offer.transaction_type = data["transaction_type"]
        offer.price_display = data["price_display"]
        offer.price_min = data.get("price_min")
        offer.price_max = data.get("price_max")
        offer.rent_period = data.get("rent_period") or ""
        offer.active = True
        offer.save()
        record_listing_change(
            actor=actor,
            record=offer,
            action="listing.record.updated" if offer_before else "listing.record.created",
            before=offer_before,
        )
        return listing
