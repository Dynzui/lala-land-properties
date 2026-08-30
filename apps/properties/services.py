from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from apps.accounts.capabilities import Capability
from apps.accounts.models import User
from apps.audittrail.models import AuditEvent, CatalogRevision

from .models import Development, Location, Property, PropertyType, Variant

CATALOG_MODELS = (PropertyType, Location, Development, Variant, Property)
PRIVATE_AUDIT_FIELDS = {
    "street_address_private",
    "latitude_private",
    "longitude_private",
    "unit_or_lot_number_private",
}
SYSTEM_FIELDS = {"id", "created_at", "updated_at"}


def serialize_catalog_record(record) -> dict:
    if not isinstance(record, CATALOG_MODELS):
        raise TypeError("Unsupported catalogue model.")
    snapshot = {}
    for field in record._meta.concrete_fields:
        if field.name in SYSTEM_FIELDS:
            continue
        value = getattr(record, field.attname)
        if isinstance(value, (UUID, Decimal, date, datetime)):
            value = str(value)
        snapshot[field.attname] = value
    return snapshot


def public_audit_snapshot(snapshot: dict) -> dict:
    return {
        key: value
        for key, value in snapshot.items()
        if key.removesuffix("_id") not in PRIVATE_AUDIT_FIELDS and key not in PRIVATE_AUDIT_FIELDS
    }


@transaction.atomic
def record_catalog_change(
    *,
    actor: User,
    record,
    action: str,
    before: dict | None = None,
    change_summary: str = "",
) -> CatalogRevision:
    if not actor.has_capability(Capability.PROPERTY_MANAGE):
        raise PermissionDenied("Catalogue management requires Owner or Admin access.")
    snapshot = serialize_catalog_record(record)
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
    AuditEvent.objects.create(
        actor=actor,
        action=action,
        target_type=entity_type,
        target_id=str(record.pk),
        metadata={
            "before": public_audit_snapshot(before or {}),
            "after": public_audit_snapshot(snapshot),
            "revision_id": str(revision.pk),
        },
    )
    return revision


@transaction.atomic
def restore_catalog_revision(*, actor: User, record, revision: CatalogRevision):
    if not actor.has_capability(Capability.PROPERTY_MANAGE):
        raise PermissionDenied("Catalogue restoration requires Owner or Admin access.")
    if revision.entity_type != record._meta.label or revision.entity_id != record.pk:
        raise ValueError("Revision does not belong to this catalogue record.")
    before = serialize_catalog_record(record)
    editable_attnames = {
        field.attname for field in record._meta.concrete_fields if field.name not in SYSTEM_FIELDS
    }
    for field_name, value in revision.snapshot.items():
        if field_name in editable_attnames:
            setattr(record, field_name, value)
    record.save()
    record_catalog_change(
        actor=actor,
        record=record,
        action="catalogue.revision.restored",
        before=before,
        change_summary=f"Restored revision {revision.revision_number}",
    )
    return record


@transaction.atomic
def archive_catalog_record(*, actor: User, record, reason: str = ""):
    if not actor.has_capability(Capability.PROPERTY_MANAGE):
        raise PermissionDenied("Catalogue archiving requires Owner or Admin access.")
    if not isinstance(record, (Development, Variant, Property)):
        raise TypeError("This catalogue record does not support archiving.")
    before = serialize_catalog_record(record)
    record.archived_at = timezone.now()
    if isinstance(record, (Development, Variant)):
        record.status = record.Status.ARCHIVED
    record.save()
    record_catalog_change(
        actor=actor,
        record=record,
        action="catalogue.record.archived",
        before=before,
        change_summary=reason or "Archived",
    )
    return record


@transaction.atomic
def reactivate_catalog_record(*, actor: User, record, reason: str = ""):
    if not actor.has_capability(Capability.PROPERTY_MANAGE):
        raise PermissionDenied("Catalogue reactivation requires Owner or Admin access.")
    if not isinstance(record, (Development, Variant, Property)):
        raise TypeError("This catalogue record does not support reactivation.")
    before = serialize_catalog_record(record)
    record.archived_at = None
    if isinstance(record, (Development, Variant)):
        record.status = record.Status.DRAFT
    record.save()
    record_catalog_change(
        actor=actor,
        record=record,
        action="catalogue.record.reactivated",
        before=before,
        change_summary=reason or "Reactivated as draft",
    )
    return record
