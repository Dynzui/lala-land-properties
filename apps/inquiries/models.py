import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from wagtail.admin.panels import FieldPanel, MultiFieldPanel


class Inquiry(models.Model):
    class Status(models.TextChoices):
        NEW = "NEW", "New"
        CONTACTED = "CONTACTED", "Contacted"
        QUALIFIED = "QUALIFIED", "Qualified"
        VIEWING = "VIEWING", "Viewing arranged"
        CLOSED_WON = "CLOSED_WON", "Closed — successful"
        CLOSED_LOST = "CLOSED_LOST", "Closed — not proceeding"
        SPAM = "SPAM", "Spam"
        ARCHIVED = "ARCHIVED", "Archived"

    class Interest(models.TextChoices):
        FIRST_HOME = "FIRST_HOME", "My first home"
        FAMILY_HOME = "FAMILY_HOME", "A family home"
        INVESTMENT = "INVESTMENT", "An investment property"
        LOT = "LOT", "A lot"
        COMMERCIAL = "COMMERCIAL", "A commercial property"
        RENTAL = "RENTAL", "A rental"
        EXPLORING = "EXPLORING", "I’m still exploring"
        SPECIFIC = "SPECIFIC", "A specific property"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(
        "listings.Listing",
        blank=True,
        null=True,
        on_delete=models.PROTECT,
        related_name="inquiries",
    )
    listing_title_snapshot = models.CharField(max_length=180, blank=True)
    name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=32, blank=True)
    interest = models.CharField(max_length=20, choices=Interest.choices)
    preferred_location = models.CharField(max_length=160, blank=True)
    budget = models.CharField(max_length=100, blank=True)
    timeline = models.CharField(max_length=100, blank=True)
    message = models.TextField(max_length=3000)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.NEW)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.PROTECT,
        related_name="assigned_inquiries",
    )
    consent_given_at = models.DateTimeField()
    privacy_notice_version = models.CharField(max_length=32, default="placeholder-v1")
    archived_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    panels = [
        MultiFieldPanel(
            [FieldPanel("name"), FieldPanel("email")],
            heading="Contact (phone requires separate approved access)",
        ),
        MultiFieldPanel(
            [
                FieldPanel("listing"),
                FieldPanel("interest"),
                FieldPanel("preferred_location"),
                FieldPanel("budget"),
                FieldPanel("timeline"),
                FieldPanel("message"),
            ],
            heading="Requirements",
        ),
        MultiFieldPanel([FieldPanel("status"), FieldPanel("assigned_to")], heading="Follow-up"),
    ]

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "assigned_to", "created_at"])]

    def __str__(self) -> str:
        return f"{self.name} — {self.get_interest_display()}"

    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower()
        self.name = self.name.strip()
        if self.listing_id and not self.listing_title_snapshot:
            self.listing_title_snapshot = self.listing.title
        if self.status == self.Status.ARCHIVED:
            self.archived_at = self.archived_at or timezone.now()
        elif self.archived_at:
            self.archived_at = None
        self.full_clean()
        return super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if self.assigned_to_id and (
            self.assigned_to.status != self.assigned_to.Status.ACTIVE
            or self.assigned_to.role
            not in {self.assigned_to.Role.OWNER, self.assigned_to.Role.ADMIN}
        ):
            raise ValidationError({"assigned_to": "Assign only an active Owner or Admin."})

    @property
    def masked_phone(self) -> str:
        if not self.phone:
            return "Not provided"
        digits = "".join(character for character in self.phone if character.isdigit())
        return f"•••• ••• {digits[-4:]}" if len(digits) >= 4 else "••••"


class InquiryNote(models.Model):
    class Kind(models.TextChoices):
        NOTE = "NOTE", "Internal note"
        CALL = "CALL", "Call"
        EMAIL = "EMAIL", "Email"
        MESSAGE = "MESSAGE", "Message"
        VIEWING = "VIEWING", "Viewing"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    inquiry = models.ForeignKey(Inquiry, on_delete=models.PROTECT, related_name="notes")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="inquiry_notes"
    )
    kind = models.CharField(max_length=12, choices=Kind.choices, default=Kind.NOTE)
    body = models.TextField(max_length=3000)
    occurred_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    panels = [
        FieldPanel("inquiry"),
        FieldPanel("kind"),
        FieldPanel("body"),
        FieldPanel("occurred_at"),
    ]

    class Meta:
        ordering = ["-occurred_at", "-created_at"]

    def __str__(self) -> str:
        return f"{self.get_kind_display()} — {self.inquiry}"

    def save(self, *args, **kwargs):
        if self._state.adding and not self.author_id:
            raise ValidationError({"author": "An internal note requires an author."})
        self.full_clean()
        return super().save(*args, **kwargs)
