from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from apps.accounts.capabilities import Capability
from apps.accounts.models import User
from apps.audittrail.models import CatalogRevision
from apps.audittrail.services import record_revision, serialize_model_record

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
    return serialize_model_record(record, excluded_fields=SYSTEM_FIELDS)


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
    return record_revision(
        actor=actor,
        record=record,
        action=action,
        snapshot=snapshot,
        before=before,
        change_summary=change_summary,
        audit_snapshot=public_audit_snapshot,
    )


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
