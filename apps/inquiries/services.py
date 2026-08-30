from django.core.exceptions import PermissionDenied
from django.db import transaction

from apps.accounts.capabilities import Capability
from apps.accounts.models import User
from apps.audittrail.models import AuditEvent

from .models import Inquiry, InquiryNote


@transaction.atomic
def update_inquiry(*, actor: User, inquiry: Inquiry, status: str, assigned_to=None) -> Inquiry:
    if not actor.has_capability(Capability.INQUIRY_MANAGE):
        raise PermissionDenied("Inquiry management requires Owner or Admin access.")
    inquiry = Inquiry.objects.select_for_update().get(pk=inquiry.pk)
    before = {"status": inquiry.status, "assigned_to_id": inquiry.assigned_to_id}
    inquiry.status = status
    inquiry.assigned_to = assigned_to
    inquiry.save()
    AuditEvent.objects.create(
        actor=actor,
        action="inquiry.updated",
        target_type=inquiry._meta.label,
        target_id=str(inquiry.pk),
        metadata={
            "before": {key: str(value) if value else None for key, value in before.items()},
            "after": {
                "status": inquiry.status,
                "assigned_to_id": str(inquiry.assigned_to_id) if inquiry.assigned_to_id else None,
            },
        },
    )
    return inquiry


@transaction.atomic
def add_inquiry_note(*, actor: User, inquiry: Inquiry, kind: str, body: str) -> InquiryNote:
    if not actor.has_capability(Capability.INQUIRY_MANAGE):
        raise PermissionDenied("Inquiry management requires Owner or Admin access.")
    note = InquiryNote.objects.create(
        inquiry=inquiry,
        author=actor,
        kind=kind,
        body=body.strip(),
    )
    AuditEvent.objects.create(
        actor=actor,
        action="inquiry.note.created",
        target_type=inquiry._meta.label,
        target_id=str(inquiry.pk),
        metadata={"note_id": str(note.pk), "kind": kind},
    )
    return note
