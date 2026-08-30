import uuid

from django.conf import settings
from django.db import models


class ImmutableAuditQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise TypeError("Audit events are immutable.")

    def delete(self):
        raise TypeError("Audit events cannot be deleted.")


class AuditEvent(models.Model):
    """Append-only record of security-sensitive staff actions."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="audit_events_performed",
    )
    action = models.CharField(max_length=80)
    target_type = models.CharField(max_length=80)
    target_id = models.CharField(max_length=80, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    objects = ImmutableAuditQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.action}: {self.target_type} {self.target_id}".strip()

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise TypeError("Audit events are immutable.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise TypeError("Audit events cannot be deleted.")


class CatalogRevision(models.Model):
    """Immutable, restorable snapshot of a managed catalogue record."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entity_type = models.CharField(max_length=80)
    entity_id = models.UUIDField()
    revision_number = models.PositiveIntegerField()
    snapshot = models.JSONField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="catalog_revisions_created",
    )
    change_summary = models.CharField(max_length=240, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    objects = ImmutableAuditQuerySet.as_manager()

    class Meta:
        ordering = ["entity_type", "entity_id", "-revision_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["entity_type", "entity_id", "revision_number"],
                name="audittrail_catalog_revision_number_unique",
            )
        ]

    def __str__(self) -> str:
        return f"{self.entity_type}:{self.entity_id} revision {self.revision_number}"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise TypeError("Catalogue revisions are immutable.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise TypeError("Catalogue revisions cannot be deleted.")
