import uuid
from builtins import property as builtin_property

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.images import get_image_model_string


class CatalogueMediaQuerySet(models.QuerySet):
    def active(self):
        return self.filter(archived_at__isnull=True)


class CatalogueMedia(models.Model):
    class Kind(models.TextChoices):
        PHOTO = "PHOTO", "Property photo"
        FLOOR_PLAN = "FLOOR_PLAN", "Floor plan"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    image = models.ForeignKey(
        get_image_model_string(),
        on_delete=models.PROTECT,
        related_name="catalogue_placements",
    )
    kind = models.CharField(max_length=16, choices=Kind.choices, default=Kind.PHOTO)
    property = models.ForeignKey(
        "properties.Property",
        blank=True,
        null=True,
        on_delete=models.PROTECT,
        related_name="media",
    )
    variant = models.ForeignKey(
        "properties.Variant",
        blank=True,
        null=True,
        on_delete=models.PROTECT,
        related_name="media",
    )
    development = models.ForeignKey(
        "properties.Development",
        blank=True,
        null=True,
        on_delete=models.PROTECT,
        related_name="media",
    )
    alt_text = models.CharField(
        max_length=250,
        help_text="Describe what is visible for visitors using screen readers.",
    )
    caption = models.CharField(max_length=250, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_cover = models.BooleanField(default=False)
    archived_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = CatalogueMediaQuerySet.as_manager()

    panels = [
        FieldPanel("image"),
        FieldPanel("kind"),
        MultiFieldPanel(
            [FieldPanel("property"), FieldPanel("variant"), FieldPanel("development")],
            heading="Attach to exactly one catalogue record",
        ),
        FieldPanel("alt_text"),
        FieldPanel("caption"),
        FieldPanel("sort_order"),
        FieldPanel("is_cover"),
    ]

    class Meta:
        ordering = ["sort_order", "created_at"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(property__isnull=False, variant__isnull=True, development__isnull=True)
                    | models.Q(
                        property__isnull=True, variant__isnull=False, development__isnull=True
                    )
                    | models.Q(
                        property__isnull=True, variant__isnull=True, development__isnull=False
                    )
                ),
                name="media_catalogue_exactly_one_target",
            ),
            models.UniqueConstraint(
                fields=["property"],
                condition=models.Q(is_cover=True, archived_at__isnull=True, property__isnull=False),
                name="media_catalogue_one_property_cover",
            ),
            models.UniqueConstraint(
                fields=["variant"],
                condition=models.Q(is_cover=True, archived_at__isnull=True, variant__isnull=False),
                name="media_catalogue_one_variant_cover",
            ),
            models.UniqueConstraint(
                fields=["development"],
                condition=models.Q(
                    is_cover=True, archived_at__isnull=True, development__isnull=False
                ),
                name="media_catalogue_one_development_cover",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.target} — {self.image.title}"

    def save(self, *args, **kwargs):
        self.alt_text = self.alt_text.strip()
        with transaction.atomic():
            self.full_clean(validate_constraints=False)
            if self.is_cover and self.archived_at is None:
                filters = {"archived_at__isnull": True, "is_cover": True}
                if self.property_id:
                    filters["property_id"] = self.property_id
                elif self.variant_id:
                    filters["variant_id"] = self.variant_id
                else:
                    filters["development_id"] = self.development_id
                type(self).objects.select_for_update().filter(**filters).exclude(pk=self.pk).update(
                    is_cover=False
                )
            return super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        target_count = sum(
            bool(value) for value in (self.property_id, self.variant_id, self.development_id)
        )
        if target_count != 1:
            raise ValidationError("Attach media to exactly one property, variant, or development.")
        if not self.alt_text.strip():
            raise ValidationError({"alt_text": "Alternative text is required."})
        if self.is_cover and self.archived_at:
            raise ValidationError({"is_cover": "Archived media cannot be a cover image."})
        if self.is_cover and self.kind != self.Kind.PHOTO:
            raise ValidationError({"is_cover": "Only a property photo can be the cover image."})

    @builtin_property
    def target(self):
        return self.property or self.variant or self.development

    def archive(self):
        self.archived_at = timezone.now()
        self.is_cover = False
        self.save(update_fields=["archived_at", "is_cover", "updated_at"])
