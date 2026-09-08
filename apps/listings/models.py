import uuid
from builtins import property as builtin_property
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.fields import RichTextField

from apps.properties.models import Property, Variant


class ListingQuerySet(models.QuerySet):
    def public(self):
        return self.filter(
            workflow_status=Listing.WorkflowStatus.PUBLISHED,
            public_status__in=[
                Listing.PublicStatus.AVAILABLE,
                Listing.PublicStatus.RESERVED,
            ],
            archived_at__isnull=True,
        ).filter(
            models.Q(property__isnull=False, property__development__isnull=True)
            | models.Q(
                property__isnull=False,
                property__development__status="ACTIVE",
                property__development__archived_at__isnull=True,
            )
            | models.Q(
                variant__isnull=False,
                variant__status="ACTIVE",
                variant__archived_at__isnull=True,
                variant__development__status="ACTIVE",
                variant__development__archived_at__isnull=True,
            )
        )


class Listing(models.Model):
    class InventoryMode(models.TextChoices):
        SINGLE = "SINGLE", "Single property"
        POOLED = "POOLED", "Pooled variant inventory"

    class WorkflowStatus(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PUBLISHED = "PUBLISHED", "Published"
        ARCHIVED = "ARCHIVED", "Archived"

    class PublicStatus(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Available"
        RESERVED = "RESERVED", "Reserved"
        SOLD = "SOLD", "Sold"
        RENTED = "RENTED", "Rented"
        UNAVAILABLE = "UNAVAILABLE", "Unavailable"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property = models.ForeignKey(
        Property,
        blank=True,
        null=True,
        on_delete=models.PROTECT,
        related_name="listings",
    )
    variant = models.ForeignKey(
        Variant,
        blank=True,
        null=True,
        on_delete=models.PROTECT,
        related_name="listings",
    )
    slug = models.SlugField(max_length=220, unique=True)
    title = models.CharField(max_length=180)
    summary = models.CharField(max_length=300)
    description = RichTextField()
    inventory_mode = models.CharField(max_length=10, choices=InventoryMode.choices)
    available_quantity = models.PositiveIntegerField(blank=True, null=True)
    public_status = models.CharField(
        max_length=16,
        choices=PublicStatus.choices,
        default=PublicStatus.AVAILABLE,
    )
    workflow_status = models.CharField(
        max_length=16,
        choices=WorkflowStatus.choices,
        default=WorkflowStatus.DRAFT,
    )
    featured = models.BooleanField(default=False)
    seo_title = models.CharField(max_length=60, blank=True)
    seo_description = models.CharField(max_length=160, blank=True)
    published_at = models.DateTimeField(blank=True, null=True)
    archived_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = ListingQuerySet.as_manager()

    panels = [
        FieldPanel("title"),
        FieldPanel("slug"),
        FieldPanel("summary"),
        FieldPanel("description"),
        MultiFieldPanel(
            [
                FieldPanel("inventory_mode"),
                FieldPanel("property"),
                FieldPanel("variant"),
                FieldPanel("available_quantity"),
            ],
            heading="Inventory",
            help_text=(
                "Single property: choose Property only and leave quantity empty. "
                "Pooled variant inventory: choose Variant only and enter the number available."
            ),
        ),
        FieldPanel("public_status"),
        FieldPanel("featured"),
        MultiFieldPanel(
            [FieldPanel("seo_title"), FieldPanel("seo_description")],
            heading="Search appearance",
        ),
    ]

    class Meta:
        ordering = ["-published_at", "title"]
        indexes = [models.Index(fields=["workflow_status", "public_status", "published_at"])]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(property__isnull=False, variant__isnull=True)
                    | models.Q(property__isnull=True, variant__isnull=False)
                ),
                name="listings_listing_exactly_one_target",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        inventory_mode="SINGLE",
                        property__isnull=False,
                        variant__isnull=True,
                        available_quantity__isnull=True,
                    )
                    | models.Q(
                        inventory_mode="POOLED",
                        property__isnull=True,
                        variant__isnull=False,
                        available_quantity__isnull=False,
                    )
                ),
                name="listings_listing_inventory_mode_matches_target",
            ),
        ]

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        errors = {}
        if self.inventory_mode == self.InventoryMode.POOLED:
            if not self.variant_id:
                errors["variant"] = "Choose the development variant represented by this listing."
            if self.property_id:
                errors["property"] = "Leave Property empty for pooled variant inventory."
            if self.available_quantity is None:
                errors["available_quantity"] = "Enter how many units of this variant are available."
        elif self.inventory_mode == self.InventoryMode.SINGLE:
            if not self.property_id:
                errors["property"] = "Choose the individual property represented by this listing."
            if self.variant_id:
                errors["variant"] = "Leave Variant empty for a single-property listing."
            if self.available_quantity is not None:
                errors["available_quantity"] = "Leave quantity empty for a single-property listing."
        if errors:
            raise ValidationError(errors)
        if self.workflow_status == self.WorkflowStatus.ARCHIVED:
            self.archived_at = self.archived_at or timezone.now()
        elif self.archived_at is not None:
            raise ValidationError(
                {"archived_at": "Only archived listings may have an archived timestamp."}
            )
        if self.workflow_status == self.WorkflowStatus.PUBLISHED:
            self._validate_publishable_state()

    def _validate_publishable_state(self):
        errors = {}
        if self._state.adding or not self.offers.filter(active=True).exists():
            errors["workflow_status"] = "A published listing needs one active offer."
        location = self.property.location if self.property_id else self.variant.development.location
        if location.visibility == location.Visibility.HIDDEN or not location.public_label:
            errors["workflow_status"] = "Publishing requires a public-safe location."
        if self.property_id and self.property.inventory_status not in {
            self.property.InventoryStatus.AVAILABLE,
            self.property.InventoryStatus.RESERVED,
        }:
            errors["workflow_status"] = "The selected property is not publicly available."
        if self.property_id and self.property.development_id and (
            self.property.development.status != self.property.development.Status.ACTIVE
            or self.property.development.is_archived
        ):
            errors["workflow_status"] = "Published listings require an active development."
        if self.variant_id and (
            self.variant.status != self.variant.Status.ACTIVE
            or self.variant.development.status != self.variant.development.Status.ACTIVE
        ):
            errors["workflow_status"] = "Pooled listings require an active variant and development."
        if not self.summary.strip() or not str(self.description).strip():
            errors["workflow_status"] = "Publishing requires a summary and description."
        if errors:
            raise ValidationError(errors)

    @builtin_property
    def is_publicly_available(self) -> bool:
        available = (
            self.workflow_status == self.WorkflowStatus.PUBLISHED
            and self.public_status in {self.PublicStatus.AVAILABLE, self.PublicStatus.RESERVED}
            and self.archived_at is None
        )
        if not available:
            return False
        if self.property_id and self.property.development_id:
            development = self.property.development
            return development.status == development.Status.ACTIVE and not development.is_archived
        if self.variant_id:
            return (
                self.variant.status == self.variant.Status.ACTIVE
                and not self.variant.is_archived
                and self.variant.development.status == self.variant.development.Status.ACTIVE
                and not self.variant.development.is_archived
            )
        return True

    @builtin_property
    def public_location(self):
        if self.property_id:
            return self.property.location.as_public_dict()
        return self.variant.development.location.as_public_dict()

    def as_public_dict(self) -> dict:
        if not self.is_publicly_available:
            return {}
        offer = self.offers.filter(active=True).first()
        return {
            "id": str(self.pk),
            "slug": self.slug,
            "title": self.title,
            "summary": self.summary,
            "description": str(self.description),
            "public_status": self.public_status,
            "featured": self.featured,
            "location": self.public_location,
            "offer": offer.as_public_dict() if offer else None,
        }


class Offer(models.Model):
    class TransactionType(models.TextChoices):
        SALE = "SALE", "For sale"
        RENT = "RENT", "For rent"

    class PriceDisplay(models.TextChoices):
        EXACT = "EXACT", "Exact price"
        STARTING_AT = "STARTING_AT", "Starting at"
        RANGE = "RANGE", "Price range"
        NEGOTIABLE = "NEGOTIABLE", "Negotiable"
        CONTACT = "CONTACT", "Contact for price"

    class RentPeriod(models.TextChoices):
        DAILY = "DAILY", "Daily"
        WEEKLY = "WEEKLY", "Weekly"
        MONTHLY = "MONTHLY", "Monthly"
        YEARLY = "YEARLY", "Yearly"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="offers")
    transaction_type = models.CharField(max_length=8, choices=TransactionType.choices)
    currency = models.CharField(max_length=3, default="PHP")
    price_display = models.CharField(max_length=16, choices=PriceDisplay.choices)
    price_min = models.DecimalField(max_digits=14, decimal_places=2, blank=True, null=True)
    price_max = models.DecimalField(max_digits=14, decimal_places=2, blank=True, null=True)
    rent_period = models.CharField(max_length=8, choices=RentPeriod.choices, blank=True)
    deposit_amount = models.DecimalField(max_digits=14, decimal_places=2, blank=True, null=True)
    minimum_lease_months = models.PositiveSmallIntegerField(blank=True, null=True)
    reservation_fee = models.DecimalField(max_digits=14, decimal_places=2, blank=True, null=True)
    available_from = models.DateField(blank=True, null=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    panels = [
        FieldPanel("listing"),
        FieldPanel("transaction_type"),
        FieldPanel("currency"),
        FieldPanel("price_display"),
        FieldPanel("price_min"),
        FieldPanel("price_max"),
        FieldPanel("rent_period"),
        FieldPanel("deposit_amount"),
        FieldPanel("minimum_lease_months"),
        FieldPanel("reservation_fee"),
        FieldPanel("available_from"),
        FieldPanel("active"),
    ]

    class Meta:
        verbose_name = "price and availability"
        verbose_name_plural = "prices and availability"
        ordering = ["-active", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["listing"],
                condition=models.Q(active=True),
                name="listings_offer_one_active_per_listing",
            ),
            models.CheckConstraint(
                condition=models.Q(price_min__isnull=True) | models.Q(price_min__gt=0),
                name="listings_offer_price_min_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(price_max__isnull=True) | models.Q(price_max__gt=0),
                name="listings_offer_price_max_positive",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(price_max__isnull=True)
                    | models.Q(price_min__isnull=True)
                    | models.Q(price_max__gte=models.F("price_min"))
                ),
                name="listings_offer_price_range_ordered",
            ),
            models.CheckConstraint(
                condition=models.Q(deposit_amount__isnull=True) | models.Q(deposit_amount__gte=0),
                name="listings_offer_deposit_nonnegative",
            ),
            models.CheckConstraint(
                condition=models.Q(reservation_fee__isnull=True) | models.Q(reservation_fee__gte=0),
                name="listings_offer_reservation_fee_nonnegative",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.listing} — {self.get_transaction_type_display()}"

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        errors = {}
        self.currency = self.currency.strip().upper()
        if len(self.currency) != 3 or not self.currency.isalpha():
            errors["currency"] = "Use a three-letter currency code such as PHP."
        if self.price_display in {self.PriceDisplay.EXACT, self.PriceDisplay.STARTING_AT}:
            if self.price_min is None or self.price_max is not None:
                errors["price_min"] = "This price format requires one price only."
        elif self.price_display == self.PriceDisplay.RANGE:
            if self.price_min is None or self.price_max is None:
                errors["price_max"] = "Price ranges require minimum and maximum prices."
        elif self.price_display == self.PriceDisplay.CONTACT and (
            self.price_min is not None or self.price_max is not None
        ):
            errors["price_min"] = "Contact pricing cannot expose numeric prices."
        if self.transaction_type == self.TransactionType.RENT:
            if not self.rent_period:
                errors["rent_period"] = "Rental offers require a rent period."
            if self.reservation_fee is not None:
                errors["reservation_fee"] = "Reservation fees are for sale offers only."
        elif self.transaction_type == self.TransactionType.SALE:
            if self.rent_period:
                errors["rent_period"] = "Sale offers cannot have a rent period."
            if self.deposit_amount is not None or self.minimum_lease_months is not None:
                errors["deposit_amount"] = "Lease terms are for rental offers only."
        if errors:
            raise ValidationError(errors)

    @staticmethod
    def _format_amount(value: Decimal | None) -> str:
        if value is None:
            return ""
        return f"{value:,.0f}"

    @builtin_property
    def display_price(self) -> str:
        symbol = "₱" if self.currency == "PHP" else f"{self.currency} "
        suffix = f" / {self.get_rent_period_display().lower()}" if self.rent_period else ""
        if self.price_display == self.PriceDisplay.CONTACT:
            return "Contact for price"
        if self.price_display == self.PriceDisplay.NEGOTIABLE:
            if self.price_min is None:
                return "Price negotiable"
            return f"{symbol}{self._format_amount(self.price_min)} negotiable{suffix}"
        if self.price_display == self.PriceDisplay.STARTING_AT:
            return f"From {symbol}{self._format_amount(self.price_min)}{suffix}"
        if self.price_display == self.PriceDisplay.RANGE:
            return (
                f"{symbol}{self._format_amount(self.price_min)}–"
                f"{symbol}{self._format_amount(self.price_max)}{suffix}"
            )
        return f"{symbol}{self._format_amount(self.price_min)}{suffix}"

    def as_public_dict(self) -> dict:
        data = {
            "transaction_type": self.transaction_type,
            "currency": self.currency,
            "price_display": self.price_display,
            "rent_period": self.rent_period or None,
            "available_from": self.available_from,
        }
        if self.price_display != self.PriceDisplay.CONTACT:
            data["price_min"] = self.price_min
            data["price_max"] = self.price_max
        return data
