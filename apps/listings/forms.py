from decimal import Decimal

from django import forms

from apps.properties.geography import (
    city_choices,
    province_choices,
    region_choices,
    validate_geography,
)
from apps.properties.models import PropertyType


class ListingFilterForm(forms.Form):
    transaction = forms.ChoiceField(
        required=False,
        choices=[("", "Sale or rent"), ("SALE", "For sale"), ("RENT", "For rent")],
    )
    property_type = forms.ModelChoiceField(
        required=False,
        empty_label="All property types",
        queryset=PropertyType.objects.none(),
        to_field_name="slug",
    )
    region = forms.ChoiceField(required=False, choices=())
    province = forms.ChoiceField(required=False, choices=())
    city_municipality = forms.ChoiceField(required=False, choices=())
    min_price = forms.DecimalField(
        required=False,
        min_value=Decimal("0"),
        decimal_places=0,
        widget=forms.NumberInput(attrs={"min": "0", "step": "100000", "placeholder": "Minimum"}),
    )
    max_price = forms.DecimalField(
        required=False,
        min_value=Decimal("0"),
        decimal_places=0,
        widget=forms.NumberInput(attrs={"min": "0", "step": "100000", "placeholder": "Maximum"}),
    )
    bedrooms = forms.ChoiceField(
        required=False,
        choices=[
            ("", "Any bedrooms"),
            ("1", "1+ bedroom"),
            ("2", "2+ bedrooms"),
            ("3", "3+ bedrooms"),
        ],
    )
    status = forms.ChoiceField(
        required=False,
        choices=[
            ("", "Available or reserved"),
            ("AVAILABLE", "Available"),
            ("RESERVED", "Reserved"),
        ],
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["property_type"].queryset = PropertyType.objects.filter(active=True)
        self.fields["region"].choices = [("", "All regions"), *region_choices()]
        self.fields["province"].choices = [("", "All provinces"), *province_choices()]
        self.fields["city_municipality"].choices = [
            ("", "All cities and municipalities"),
            *city_choices(),
        ]
        for name in ("region", "province", "city_municipality"):
            self.fields[name].widget.attrs["data-geography-field"] = name
        self.fields["region"].widget.attrs["data-geography-url"] = "/geography/"

    def clean(self):
        cleaned = super().clean()
        region, province, city = (
            cleaned.get("region"),
            cleaned.get("province"),
            cleaned.get("city_municipality"),
        )
        if city and (not region or not validate_geography(region, province, city)):
            self.add_error(
                "city_municipality",
                "Choose a city or municipality from the selected region and province.",
            )
        elif province and not region:
            self.add_error("province", "Choose a region first.")
        minimum = cleaned.get("min_price")
        maximum = cleaned.get("max_price")
        if minimum is not None and maximum is not None and minimum > maximum:
            self.add_error("max_price", "Maximum price must be at least the minimum price.")
        return cleaned
