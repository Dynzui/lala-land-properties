from django import forms
from wagtail.admin.forms.models import WagtailAdminModelForm

from apps.accounts.models import User

from .geography import (
    INDEPENDENT,
    city_choices,
    normalize_province,
    province_choices,
    region_choices,
    validate_geography,
)
from .models import Location
from .widgets import MapCoordinateWidget


class LocationAdminForm(WagtailAdminModelForm):
    """Let Admins maintain public geography without exposing exact private data."""

    class Meta:
        model = Location
        fields = [
            "country_code",
            "region",
            "province",
            "city_municipality",
            "barangay",
            "subdivision_area",
            "public_label",
            "visibility",
            "public_latitude",
            "public_longitude",
            "street_address_private",
            "latitude_private",
            "longitude_private",
        ]
        widgets = {
            "public_latitude": MapCoordinateWidget(map_name="public", axis="latitude"),
            "public_longitude": MapCoordinateWidget(map_name="public", axis="longitude"),
            "latitude_private": MapCoordinateWidget(map_name="private", axis="latitude"),
            "longitude_private": MapCoordinateWidget(map_name="private", axis="longitude"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["region"].choices = [("", "Select a region"), *region_choices()]
        self.fields["province"].choices = [("", "Select a province"), *province_choices()]
        self.fields["city_municipality"].choices = [
            ("", "Select a city or municipality"),
            *city_choices(),
        ]
        for name in ("region", "province", "city_municipality"):
            self.fields[name].widget.attrs["data-geography-field"] = name
        self.fields["region"].widget.attrs["data-geography-url"] = "/geography/"
        if self.instance and self.instance.pk and not self.is_bound and not self.instance.province:
            self.initial["province"] = INDEPENDENT
        if not self.for_user or self.for_user.role != User.Role.OWNER:
            for field_name in ("street_address_private", "latitude_private", "longitude_private"):
                self.fields.pop(field_name, None)

    def clean_province(self):
        return normalize_province(self.cleaned_data["province"])

    def clean(self):
        cleaned = super().clean()
        if all(
            cleaned.get(name) is not None for name in ("region", "province", "city_municipality")
        ):
            if not validate_geography(
                cleaned.get("region"), cleaned.get("province"), cleaned.get("city_municipality")
            ):
                self.add_error(
                    "city_municipality",
                    "Choose a city or municipality belonging to the selected region and province.",
                )
        return cleaned

    class Media:
        js = ("js/philippine-geography.js",)

    region = forms.ChoiceField(choices=(), label="Region")
    province = forms.ChoiceField(choices=(), label="Province")
    city_municipality = forms.ChoiceField(choices=(), label="City / municipality")
