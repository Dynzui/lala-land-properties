from django.urls import path, reverse
from wagtail import hooks
from wagtail.admin.menu import MenuItem
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import CreateView, SnippetViewSet

from apps.accounts.capabilities import Capability
from apps.audittrail.models import AuditEvent

from .admin_views import inquiry_dashboard, inquiry_detail
from .forms import InquiryAdminForm
from .models import Inquiry, InquiryNote


class InquiryViewSet(SnippetViewSet):
    model = Inquiry
    icon = "mail"
    list_display = [
        "name",
        "property_reference",
        "interest",
        "status",
        "assignment_summary",
        "contact_summary",
        "created_at",
    ]
    list_filter = ["status", "interest", "assigned_to"]
    search_fields = ["name", "email", "listing_title_snapshot", "message"]
    ordering = ["-created_at"]

    def get_form_class(self, for_update=False):
        return InquiryAdminForm


class InquiryNoteCreateView(CreateView):
    def save_instance(self):
        self.form.instance.author = self.request.user
        return super().save_instance()


class InquiryNoteViewSet(SnippetViewSet):
    model = InquiryNote
    add_view_class = InquiryNoteCreateView
    icon = "comment"
    list_display = ["inquiry", "kind", "author", "occurred_at"]
    list_filter = ["kind", "author"]
    search_fields = ["inquiry__name", "body"]
    ordering = ["-occurred_at"]


register_snippet(Inquiry, viewset=InquiryViewSet)
register_snippet(InquiryNote, viewset=InquiryNoteViewSet)


class InquiryDashboardMenuItem(MenuItem):
    def is_shown(self, request):
        return request.user.has_capability(Capability.INQUIRY_MANAGE)


@hooks.register("register_admin_urls")
def register_inquiry_admin_urls():
    return [
        path("inquiries/", inquiry_dashboard, name="lala_inquiry_dashboard"),
        path(
            "inquiries/<uuid:inquiry_id>/",
            inquiry_detail,
            name="lala_inquiry_detail",
        ),
    ]


@hooks.register("register_admin_menu_item")
def register_inquiry_dashboard_menu_item():
    return InquiryDashboardMenuItem(
        "Inquiry dashboard",
        reverse("lala_inquiry_dashboard"),
        icon_name="mail",
        order=250,
    )


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
