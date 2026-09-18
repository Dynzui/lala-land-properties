from django.core.exceptions import PermissionDenied
from django.db import transaction

from apps.accounts.capabilities import Capability
from apps.accounts.models import User
from apps.audittrail.models import AuditEvent

from .models import CatalogueMedia


def media_snapshot(media: CatalogueMedia) -> dict:
    return {
        "image_id": media.image_id,
        "kind": media.kind,
        "property_id": str(media.property_id) if media.property_id else None,
        "variant_id": str(media.variant_id) if media.variant_id else None,
        "development_id": str(media.development_id) if media.development_id else None,
        "alt_text": media.alt_text,
        "caption": media.caption,
        "sort_order": media.sort_order,
        "is_cover": media.is_cover,
        "archived_at": str(media.archived_at) if media.archived_at else None,
    }


@transaction.atomic
def record_media_change(
    *, actor: User, media: CatalogueMedia, action: str, before: dict | None = None
):
    if not actor.has_capability(Capability.PROPERTY_MANAGE):
        raise PermissionDenied("Media management requires Owner or Admin access.")
    AuditEvent.objects.create(
        actor=actor,
        action=action,
        target_type=media._meta.label,
        target_id=str(media.pk),
        metadata={"before": before or {}, "after": media_snapshot(media)},
    )


def media_for_listing(listing, *, kind: str = CatalogueMedia.Kind.PHOTO) -> list[CatalogueMedia]:
    targets = []
    if listing.property_id:
        targets.append({"property_id": listing.property_id})
        if listing.property.variant_id:
            targets.append({"variant_id": listing.property.variant_id})
        if listing.property.development_id:
            targets.append({"development_id": listing.property.development_id})
    else:
        targets.append({"variant_id": listing.variant_id})
        targets.append({"development_id": listing.variant.development_id})
    for target in targets:
        media = list(
            CatalogueMedia.objects.active()
            .filter(kind=kind, **target)
            .select_related("image")
            .order_by("-is_cover", "sort_order", "created_at")
        )
        if media:
            return media
    return []
