from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from apps.accounts.capabilities import Capability
from apps.accounts.models import User
from apps.audittrail.models import AuditEvent, CatalogRevision
from apps.properties.models import Development, Location, Property, Variant

from .models import Listing, Offer


def serialize_record(record) -> dict:
    snapshot = {}
    for field in record._meta.concrete_fields:
        if field.name in {"id", "created_at", "updated_at"}:
            continue
        value = getattr(record, field.attname)
        if isinstance(value, (UUID, Decimal, date, datetime)):
            value = str(value)
        snapshot[field.attname] = value
    return snapshot


@transaction.atomic
def record_listing_change(
    *, actor: User, record: Listing | Offer, action: str, before: dict | None = None
):
    if not actor.has_capability(Capability.LISTING_MANAGE):
        raise PermissionDenied("Listing management requires Owner or Admin access.")
    snapshot = serialize_record(record)
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
    )
    AuditEvent.objects.create(
        actor=actor,
        action=action,
        target_type=entity_type,
        target_id=str(record.pk),
        metadata={"before": before or {}, "after": snapshot, "revision_id": str(revision.pk)},
    )
    return revision


def validate_for_publication(listing: Listing) -> None:
    errors = {}
    offer = listing.offers.filter(active=True).first()
    if offer is None:
        errors["offer"] = "A listing needs one active sale or rental offer."
    location = (
        listing.property.location if listing.property_id else listing.variant.development.location
    )
    if location.visibility == Location.Visibility.HIDDEN or not location.public_label:
        errors["location"] = "Publishing requires a public-safe location."
    if listing.property_id and listing.property.inventory_status not in {
        Property.InventoryStatus.AVAILABLE,
        Property.InventoryStatus.RESERVED,
    }:
        errors["property"] = "The selected property is not publicly available."
    if listing.variant_id and (
        listing.variant.status != Variant.Status.ACTIVE
        or listing.variant.development.status != Development.Status.ACTIVE
    ):
        errors["variant"] = "Pooled listings require an active variant and development."
    if not listing.summary.strip() or not str(listing.description).strip():
        errors["content"] = "A summary and description are required."
    if errors:
        raise ValidationError(errors)


@transaction.atomic
def publish_listing(*, actor: User, listing: Listing) -> Listing:
    if not actor.has_capability(Capability.LISTING_PUBLISH):
        raise PermissionDenied("Publishing requires Owner or Admin access.")
    listing = Listing.objects.select_for_update().get(pk=listing.pk)
    validate_for_publication(listing)
    before = serialize_record(listing)
    listing.workflow_status = Listing.WorkflowStatus.PUBLISHED
    listing.archived_at = None
    if listing.published_at is None:
        listing.published_at = timezone.now()
    listing.save()
    record_listing_change(
        actor=actor,
        record=listing,
        action="listing.published",
        before=before,
    )
    return listing


@transaction.atomic
def archive_listing(*, actor: User, listing: Listing) -> Listing:
    if not actor.has_capability(Capability.LISTING_MANAGE):
        raise PermissionDenied("Archiving requires Owner or Admin access.")
    listing = Listing.objects.select_for_update().get(pk=listing.pk)
    before = serialize_record(listing)
    listing.workflow_status = Listing.WorkflowStatus.ARCHIVED
    listing.archived_at = timezone.now()
    listing.save()
    record_listing_change(
        actor=actor,
        record=listing,
        action="listing.archived",
        before=before,
    )
    return listing


@transaction.atomic
def restore_listing(*, actor: User, listing: Listing) -> Listing:
    """Restore an archived listing as a draft so it can be reviewed before republishing."""
    if not actor.has_capability(Capability.LISTING_MANAGE):
        raise PermissionDenied("Restoring requires Owner or Admin access.")
    listing = Listing.objects.select_for_update().get(pk=listing.pk)
    if listing.workflow_status != Listing.WorkflowStatus.ARCHIVED:
        raise ValidationError({"workflow_status": "Only archived listings can be restored."})
    before = serialize_record(listing)
    listing.workflow_status = Listing.WorkflowStatus.DRAFT
    listing.archived_at = None
    listing.save()
    record_listing_change(
        actor=actor,
        record=listing,
        action="listing.restored",
        before=before,
    )
    return listing


@transaction.atomic
def set_public_status(*, actor: User, listing: Listing, status: str) -> Listing:
    if not actor.has_capability(Capability.LISTING_MANAGE):
        raise PermissionDenied("Status changes require Owner or Admin access.")
    if status not in Listing.PublicStatus.values:
        raise ValueError("Unknown public listing status.")
    listing = Listing.objects.select_for_update().get(pk=listing.pk)
    before = serialize_record(listing)
    listing.public_status = status
    listing.save()
    record_listing_change(
        actor=actor,
        record=listing,
        action="listing.public_status.changed",
        before=before,
    )
    return listing
