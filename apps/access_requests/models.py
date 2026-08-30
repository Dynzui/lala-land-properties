import uuid

from django.conf import settings
from django.db import models

from apps.properties.models import Location


class SensitiveAccessRequest(models.Model):
    class Scope(models.TextChoices):
        EXACT_LOCATION = "EXACT_LOCATION", "Exact location"
        PHONE_NUMBER = "PHONE_NUMBER", "Customer phone numbers"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        DENIED = "DENIED", "Denied"
        CANCELLED = "CANCELLED", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="sensitive_access_requests",
    )
    scope = models.CharField(max_length=24, choices=Scope.choices)
    location = models.ForeignKey(
        Location,
        blank=True,
        null=True,
        on_delete=models.PROTECT,
        related_name="access_requests",
    )
    reason = models.CharField(max_length=500)
    requested_minutes = models.PositiveSmallIntegerField(default=60)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.PROTECT,
        related_name="sensitive_access_reviews",
    )
    review_note = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.requester} — {self.get_scope_display()} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if self.scope == self.Scope.EXACT_LOCATION and self.location_id is None:
            from django.core.exceptions import ValidationError

            raise ValidationError({"location": "Exact-location requests require a location."})
        if self.scope == self.Scope.PHONE_NUMBER and self.location_id is not None:
            from django.core.exceptions import ValidationError

            raise ValidationError({"location": "Phone access is not tied to a location."})


class SensitiveAccessGrant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    grantee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="sensitive_access_grants",
    )
    scope = models.CharField(max_length=24, choices=SensitiveAccessRequest.Scope.choices)
    location = models.ForeignKey(
        Location,
        blank=True,
        null=True,
        on_delete=models.PROTECT,
        related_name="access_grants",
    )
    source_request = models.ForeignKey(
        SensitiveAccessRequest,
        on_delete=models.PROTECT,
        related_name="grants",
    )
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="sensitive_access_grants_issued",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(blank=True, null=True)
    revoked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.PROTECT,
        related_name="sensitive_access_grants_revoked",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["grantee", "scope", "expires_at"])]

    def __str__(self) -> str:
        return f"{self.grantee} — {self.get_scope_display()}"
