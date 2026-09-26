from collections.abc import Callable, Collection
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from django.db import transaction
from django.db.models import Max, Model

from .models import AuditEvent, CatalogRevision

DEFAULT_SYSTEM_FIELDS = frozenset({"id", "created_at", "updated_at"})


def serialize_model_record(
    record: Model,
    *,
    excluded_fields: Collection[str] = DEFAULT_SYSTEM_FIELDS,
) -> dict:
    """Return a JSON-safe snapshot of a model's concrete database fields."""
    snapshot = {}
    for field in record._meta.concrete_fields:
        if field.name in excluded_fields:
            continue
        value = getattr(record, field.attname)
        if isinstance(value, (UUID, Decimal, date, datetime)):
            value = str(value)
        snapshot[field.attname] = value
    return snapshot


@transaction.atomic
def record_revision(
    *,
    actor,
    record: Model,
    action: str,
    snapshot: dict,
    before: dict | None = None,
    change_summary: str = "",
    audit_snapshot: Callable[[dict], dict] | None = None,
) -> CatalogRevision:
    """Append an immutable revision and its matching audit event."""
    entity_type = record._meta.label
    latest = (
        CatalogRevision.objects.select_for_update()
        .filter(entity_type=entity_type, entity_id=record.pk)
        .aggregate(number=Max("revision_number"))["number"]
        or 0
    )
    revision = CatalogRevision.objects.create(
        entity_type=entity_type,
        entity_id=record.pk,
        revision_number=latest + 1,
        snapshot=snapshot,
        created_by=actor,
        change_summary=change_summary,
    )
    sanitize = audit_snapshot or (lambda value: value)
    AuditEvent.objects.create(
        actor=actor,
        action=action,
        target_type=entity_type,
        target_id=str(record.pk),
        metadata={
            "before": sanitize(before or {}),
            "after": sanitize(snapshot),
            "revision_id": str(revision.pk),
        },
    )
    return revision
