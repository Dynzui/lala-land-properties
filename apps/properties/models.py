import uuid
from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.fields import RichTextField


class TimestampedUUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class PropertyType(TimestampedUUIDModel):
    SUPPORTED_FIELDS = frozenset(
        {
            "bedrooms",
            "bathrooms",
            "parking_spaces",
            "floor_area_sqm",
            "lot_area_sqm",
            "furnishing",
            "memorial_capacity",
        }
    )

    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    description = models.TextField(blank=True)
    applicable_fields = models.JSONField(default=list, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)

    panels = [
        FieldPanel("name"),
        FieldPanel("slug"),
        FieldPanel("description"),
        FieldPanel(
            "applicable_fields",
            widget=forms.CheckboxSelectMultiple(
                choices=[
                    (field, field.replace("_", " ").title()) for field in sorted(SUPPORTED_FIELDS)
                ]
            ),
        ),
        FieldPanel("sort_order"),
        FieldPanel("active"),
    ]

    class Meta:
        ordering = ["sort_order", "name"]
        constraints = [
            models.UniqueConstraint(Lower("name"), name="properties_type_name_ci_unique"),
        ]

    def __str__(self) -> str:
        return self.name

    def clean(self):
        super().clean()
        fields = self.applicable_fields
        if not isinstance(fields, list) or any(not isinstance(item, str) for item in fields):
            raise ValidationError({"applicable_fields": "Use a list of supported field names."})
        unsupported = set(fields) - self.SUPPORTED_FIELDS
        if unsupported:
            raise ValidationError(
                {"applicable_fields": f"Unsupported fields: {', '.join(sorted(unsupported))}."}
            )
        if len(fields) != len(set(fields)):
            raise ValidationError({"applicable_fields": "Field names cannot be repeated."})


class Location(TimestampedUUIDModel):
    class Visibility(models.TextChoices):
        EXACT = "EXACT", "Exact public pin"
        APPROXIMATE = "APPROXIMATE", "Approximate public pin"
        AREA_ONLY = "AREA_ONLY", "Area label only"
        HIDDEN = "HIDDEN", "Hidden"

    country_code = models.CharField(max_length=2, default="PH")
    region = models.CharField(max_length=120, blank=True)
    province = models.CharField(max_length=120, blank=True)
    city_municipality = models.CharField(max_length=120)
    barangay = models.CharField(max_length=120, blank=True)
    subdivision_area = models.CharField(max_length=180, blank=True)
    street_address_private = models.TextField(blank=True)
    latitude_private = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude_private = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    public_label = models.CharField(max_length=220)
    visibility = models.CharField(
        max_length=16, choices=Visibility.choices, default=Visibility.AREA_ONLY
    )
    public_latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    public_longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)

    panels = [
        MultiFieldPanel(
            [
                FieldPanel("country_code"),
                FieldPanel("region"),
                FieldPanel("province"),
                FieldPanel("city_municipality"),
                FieldPanel("barangay"),
                FieldPanel("subdivision_area"),
            ],
            heading="Area",
        ),
        MultiFieldPanel(
            [
                FieldPanel("public_label"),
                FieldPanel("visibility"),
                FieldPanel("public_latitude"),
                FieldPanel("public_longitude"),
            ],
            heading="Public location",
        ),
        MultiFieldPanel(
            [
                FieldPanel("street_address_private"),
                FieldPanel("latitude_private"),
                FieldPanel("longitude_private"),
            ],
            heading="Private exact location — Owner access only",
        ),
    ]

    class Meta:
        ordering = ["province", "city_municipality", "public_label"]
        indexes = [models.Index(fields=["province", "city_municipality", "barangay"])]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(latitude_private__isnull=True, longitude_private__isnull=True)
                    | models.Q(latitude_private__isnull=False, longitude_private__isnull=False)
                ),
                name="properties_location_private_coordinates_pair",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(public_latitude__isnull=True, public_longitude__isnull=True)
                    | models.Q(public_latitude__isnull=False, public_longitude__isnull=False)
                ),
                name="properties_location_public_coordinates_pair",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(latitude_private__isnull=True)
                    | models.Q(latitude_private__gte=-90, latitude_private__lte=90)
                ),
                name="properties_location_private_latitude_range",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(longitude_private__isnull=True)
                    | models.Q(longitude_private__gte=-180, longitude_private__lte=180)
                ),
                name="properties_location_private_longitude_range",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(public_latitude__isnull=True)
                    | models.Q(public_latitude__gte=-90, public_latitude__lte=90)
                ),
                name="properties_location_public_latitude_range",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(public_longitude__isnull=True)
                    | models.Q(public_longitude__gte=-180, public_longitude__lte=180)
                ),
                name="properties_location_public_longitude_range",
            ),
            models.CheckConstraint(
                condition=(
                    ~models.Q(visibility__in=["EXACT", "APPROXIMATE"])
                    | models.Q(public_latitude__isnull=False, public_longitude__isnull=False)
                ),
                name="properties_location_public_pin_coordinates_required",
            ),
        ]

    def __str__(self) -> str:
        return self.public_label

    def clean(self):
        super().clean()
        self._validate_coordinate_pair("latitude_private", "longitude_private")
        self._validate_coordinate_pair("public_latitude", "public_longitude")
        if self.visibility in {self.Visibility.EXACT, self.Visibility.APPROXIMATE} and (
            self.public_latitude is None or self.public_longitude is None
        ):
            raise ValidationError(
                {"public_latitude": "A public coordinate pair is required for public map pins."}
            )

    def _validate_coordinate_pair(self, latitude_field: str, longitude_field: str):
        latitude = getattr(self, latitude_field)
        longitude = getattr(self, longitude_field)
        if (latitude is None) != (longitude is None):
            raise ValidationError(
                {latitude_field: "Latitude and longitude must be supplied together."}
            )
        if latitude is not None and not Decimal("-90") <= latitude <= Decimal("90"):
            raise ValidationError({latitude_field: "Latitude must be between -90 and 90."})
        if longitude is not None and not Decimal("-180") <= longitude <= Decimal("180"):
            raise ValidationError({longitude_field: "Longitude must be between -180 and 180."})

    def as_public_dict(self) -> dict:
        if self.visibility == self.Visibility.HIDDEN:
            return {"visibility": self.Visibility.HIDDEN}
        data = {
            "public_label": self.public_label,
            "visibility": self.visibility,
            "city_municipality": self.city_municipality,
            "province": self.province,
        }
        if self.visibility in {self.Visibility.EXACT, self.Visibility.APPROXIMATE}:
            data["latitude"] = self.public_latitude
            data["longitude"] = self.public_longitude
        return data


class ArchivableModel(TimestampedUUIDModel):
    archived_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        abstract = True

    @property
    def is_archived(self) -> bool:
        return self.archived_at is not None


class Development(ArchivableModel):
    class Type(models.TextChoices):
        SUBDIVISION = "SUBDIVISION", "Subdivision"
        CONDOMINIUM = "CONDOMINIUM", "Condominium"
        COMMERCIAL = "COMMERCIAL", "Commercial"
        MEMORIAL_PARK = "MEMORIAL_PARK", "Memorial park"
        MIXED_USE = "MIXED_USE", "Mixed use"
        OTHER = "OTHER", "Other"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"
        ARCHIVED = "ARCHIVED", "Archived"

    location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name="developments")
    name = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200, unique=True)
    development_type = models.CharField(max_length=20, choices=Type.choices)
    summary = models.CharField(max_length=300)
    description = RichTextField()
    developer_name = models.CharField(max_length=180, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    published_at = models.DateTimeField(blank=True, null=True)

    panels = [
        FieldPanel("name"),
        FieldPanel("slug"),
        FieldPanel("development_type"),
        FieldPanel("location"),
        FieldPanel("summary"),
        FieldPanel("description"),
        FieldPanel("developer_name"),
        FieldPanel("status"),
    ]

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def clean(self):
        super().clean()
        if self.status == self.Status.ACTIVE and self.published_at is None:
            self.published_at = timezone.now()
        if self.status == self.Status.ARCHIVED and self.archived_at is None:
            self.archived_at = timezone.now()
        if self.status != self.Status.ARCHIVED and self.archived_at is not None:
            raise ValidationError({"status": "Archived records must keep ARCHIVED status."})

    def as_public_dict(self) -> dict:
        if self.status != self.Status.ACTIVE or self.is_archived:
            return {}
        return {
            "id": str(self.pk),
            "name": self.name,
            "slug": self.slug,
            "development_type": self.development_type,
            "summary": self.summary,
            "description": str(self.description),
            "developer_name": self.developer_name,
            "location": self.location.as_public_dict(),
        }


class Variant(ArchivableModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"
        ARCHIVED = "ARCHIVED", "Archived"

    development = models.ForeignKey(Development, on_delete=models.PROTECT, related_name="variants")
    property_type = models.ForeignKey(
        PropertyType, on_delete=models.PROTECT, related_name="variants"
    )
    name = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200)
    description = RichTextField()
    bedrooms = models.PositiveSmallIntegerField(blank=True, null=True)
    bathrooms = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True)
    floor_area_sqm = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    lot_area_sqm = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    memorial_capacity = models.PositiveSmallIntegerField(blank=True, null=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)

    panels = [
        FieldPanel("development"),
        FieldPanel("property_type"),
        FieldPanel("name"),
        FieldPanel("slug"),
        FieldPanel("description"),
        MultiFieldPanel(
            [
                FieldPanel("bedrooms"),
                FieldPanel("bathrooms"),
                FieldPanel("floor_area_sqm"),
                FieldPanel("lot_area_sqm"),
                FieldPanel("memorial_capacity"),
            ],
            heading="Specifications",
        ),
        FieldPanel("status"),
    ]

    class Meta:
        ordering = ["development", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["development", "slug"],
                name="properties_variant_development_slug_unique",
            ),
            models.UniqueConstraint(
                Lower("name"),
                "development",
                name="properties_variant_development_name_ci_unique",
            ),
            models.CheckConstraint(
                condition=models.Q(bathrooms__isnull=True) | models.Q(bathrooms__gte=0),
                name="properties_variant_bathrooms_nonnegative",
            ),
            models.CheckConstraint(
                condition=models.Q(floor_area_sqm__isnull=True) | models.Q(floor_area_sqm__gt=0),
                name="properties_variant_floor_area_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(lot_area_sqm__isnull=True) | models.Q(lot_area_sqm__gt=0),
                name="properties_variant_lot_area_positive",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.development} — {self.name}"

    def clean(self):
        super().clean()
        if not self.property_type.active and self._state.adding:
            raise ValidationError({"property_type": "Inactive property types cannot be assigned."})
        if self.status == self.Status.ACTIVE and (
            self.development.status != Development.Status.ACTIVE or self.development.is_archived
        ):
            raise ValidationError({"status": "An active variant requires an active development."})
        if self.status == self.Status.ARCHIVED and self.archived_at is None:
            self.archived_at = timezone.now()
        if self.status != self.Status.ARCHIVED and self.archived_at is not None:
            raise ValidationError({"status": "Archived records must keep ARCHIVED status."})

    def as_public_dict(self) -> dict:
        if self.status != self.Status.ACTIVE or self.is_archived:
            return {}
        return {
            "id": str(self.pk),
            "name": self.name,
            "slug": self.slug,
            "description": str(self.description),
            "property_type": self.property_type.name,
            "bedrooms": self.bedrooms,
            "bathrooms": self.bathrooms,
            "floor_area_sqm": self.floor_area_sqm,
            "lot_area_sqm": self.lot_area_sqm,
            "memorial_capacity": self.memorial_capacity,
            "development": self.development.as_public_dict(),
        }


class Property(ArchivableModel):
    class Furnishing(models.TextChoices):
        UNFURNISHED = "UNFURNISHED", "Unfurnished"
        SEMI_FURNISHED = "SEMI_FURNISHED", "Semi-furnished"
        FURNISHED = "FURNISHED", "Furnished"

    class Occupancy(models.TextChoices):
        VACANT = "VACANT", "Vacant"
        OCCUPIED = "OCCUPIED", "Occupied"
        OWNER_OCCUPIED = "OWNER_OCCUPIED", "Owner occupied"
        UNKNOWN = "UNKNOWN", "Unknown"

    class InventoryStatus(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Available"
        RESERVED = "RESERVED", "Reserved"
        UNDER_OFFER = "UNDER_OFFER", "Under offer"
        SOLD = "SOLD", "Sold"
        RENTED = "RENTED", "Rented"
        UNAVAILABLE = "UNAVAILABLE", "Unavailable"

    development = models.ForeignKey(
        Development, blank=True, null=True, on_delete=models.PROTECT, related_name="properties"
    )
    variant = models.ForeignKey(
        Variant, blank=True, null=True, on_delete=models.PROTECT, related_name="properties"
    )
    location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name="properties")
    property_type = models.ForeignKey(
        PropertyType, on_delete=models.PROTECT, related_name="properties"
    )
    reference_code = models.CharField(max_length=80, unique=True)
    unit_or_lot_number_private = models.CharField(max_length=120, blank=True)
    title_override = models.CharField(max_length=180, blank=True)
    bedrooms = models.PositiveSmallIntegerField(blank=True, null=True)
    bathrooms = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True)
    parking_spaces = models.PositiveSmallIntegerField(blank=True, null=True)
    floor_area_sqm = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    lot_area_sqm = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    furnishing = models.CharField(max_length=20, choices=Furnishing.choices, blank=True)
    occupancy_status = models.CharField(
        max_length=20, choices=Occupancy.choices, default=Occupancy.UNKNOWN
    )
    inventory_status = models.CharField(
        max_length=20,
        choices=InventoryStatus.choices,
        default=InventoryStatus.AVAILABLE,
    )

    panels = [
        FieldPanel("reference_code"),
        FieldPanel("property_type"),
        FieldPanel("development"),
        FieldPanel("variant"),
        FieldPanel("location"),
        FieldPanel("title_override"),
        FieldPanel("unit_or_lot_number_private"),
        MultiFieldPanel(
            [
                FieldPanel("bedrooms"),
                FieldPanel("bathrooms"),
                FieldPanel("parking_spaces"),
                FieldPanel("floor_area_sqm"),
                FieldPanel("lot_area_sqm"),
                FieldPanel("furnishing"),
                FieldPanel("occupancy_status"),
            ],
            heading="Specifications",
        ),
        FieldPanel("inventory_status"),
    ]

    class Meta:
        ordering = ["reference_code"]
        indexes = [
            models.Index(fields=["property_type", "inventory_status"]),
            models.Index(fields=["bedrooms", "lot_area_sqm"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(variant__isnull=True) | models.Q(development__isnull=False),
                name="properties_property_variant_requires_development",
            ),
            models.CheckConstraint(
                condition=models.Q(bathrooms__isnull=True) | models.Q(bathrooms__gte=0),
                name="properties_property_bathrooms_nonnegative",
            ),
            models.CheckConstraint(
                condition=models.Q(floor_area_sqm__isnull=True) | models.Q(floor_area_sqm__gt=0),
                name="properties_property_floor_area_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(lot_area_sqm__isnull=True) | models.Q(lot_area_sqm__gt=0),
                name="properties_property_lot_area_positive",
            ),
        ]

    def __str__(self) -> str:
        return self.title_override or self.reference_code

    def clean(self):
        super().clean()
        errors = {}
        if not self.property_type.active and self._state.adding:
            errors["property_type"] = "Inactive property types cannot be assigned."
        if self.variant_id:
            if self.variant.development_id != self.development_id:
                errors["variant"] = "Variant must belong to the selected development."
            if self.variant.property_type_id != self.property_type_id:
                errors["property_type"] = "Property type must match the selected variant."
        if self._state.adding:
            if self.development_id and self.development.is_archived:
                errors["development"] = "New properties cannot use an archived development."
            if self.variant_id and self.variant.is_archived:
                errors["variant"] = "New properties cannot use an archived variant."
        if errors:
            raise ValidationError(errors)

    def as_public_dict(self) -> dict:
        if self.is_archived or self.inventory_status in {
            self.InventoryStatus.SOLD,
            self.InventoryStatus.RENTED,
            self.InventoryStatus.UNAVAILABLE,
        }:
            return {}
        return {
            "id": str(self.pk),
            "title": self.title_override or self.property_type.name,
            "property_type": self.property_type.name,
            "bedrooms": self.bedrooms,
            "bathrooms": self.bathrooms,
            "parking_spaces": self.parking_spaces,
            "floor_area_sqm": self.floor_area_sqm,
            "lot_area_sqm": self.lot_area_sqm,
            "furnishing": self.furnishing,
            "inventory_status": self.inventory_status,
            "location": self.location.as_public_dict(),
        }
