from wagtail import hooks
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet

from apps.audittrail.models import AuditEvent

from .models import Inquiry, InquiryNote


class InquiryViewSet(SnippetViewSet):
    model = Inquiry
    icon = "mail"
    list_display = ["name", "interest", "status", "assigned_to", "masked_phone", "created_at"]
    list_filter = ["status", "interest", "assigned_to"]
    search_fields = ["name", "email", "listing_title_snapshot", "message"]
    ordering = ["-created_at"]


class InquiryNoteViewSet(SnippetViewSet):
    model = InquiryNote
    icon = "comment"
    list_display = ["inquiry", "kind", "author", "occurred_at"]
    list_filter = ["kind", "author"]
    search_fields = ["inquiry__name", "body"]
    ordering = ["-occurred_at"]


register_snippet(Inquiry, viewset=InquiryViewSet)
register_snippet(InquiryNote, viewset=InquiryNoteViewSet)


@hooks.register("before_create_snippet")
def set_note_author(request, instance):
    if isinstance(instance, InquiryNote):
        instance.author = request.user


@hooks.register("after_create_snippet")
def audit_inquiry_create(request, instance):
    if isinstance(instance, InquiryNote):
        AuditEvent.objects.create(
            actor=request.user,
            action="inquiry.note.created",
            target_type=instance.inquiry._meta.label,
            target_id=str(instance.inquiry_id),
            metadata={"note_id": str(instance.pk), "kind": instance.kind},
        )


@hooks.register("before_edit_snippet")
def capture_inquiry_state(request, instance):
    if isinstance(instance, Inquiry):
        request._lala_inquiry_before = {
            "status": instance.status,
            "assigned_to_id": str(instance.assigned_to_id) if instance.assigned_to_id else None,
        }


@hooks.register("after_edit_snippet")
def audit_inquiry_edit(request, instance):
    if isinstance(instance, Inquiry):
        AuditEvent.objects.create(
            actor=request.user,
            action="inquiry.updated",
            target_type=instance._meta.label,
            target_id=str(instance.pk),
            metadata={
                "before": getattr(request, "_lala_inquiry_before", {}),
                "after": {
                    "status": instance.status,
                    "assigned_to_id": (
                        str(instance.assigned_to_id) if instance.assigned_to_id else None
                    ),
                },
            },
        )
