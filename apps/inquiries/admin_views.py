from django.core.exceptions import PermissionDenied
from django.db.models import Case, Count, IntegerField, Q, Value, When
from django.shortcuts import get_object_or_404, render
from wagtail.admin.auth import require_admin_access

from apps.access_requests.models import SensitiveAccessRequest
from apps.access_requests.services import user_has_sensitive_access
from apps.accounts.capabilities import Capability
from apps.audittrail.models import AuditEvent

from .models import Inquiry, InquiryNote


def _require_inquiry_access(user):
    if not user.has_capability(Capability.INQUIRY_MANAGE):
        raise PermissionDenied


@require_admin_access
def inquiry_dashboard(request):
    _require_inquiry_access(request.user)
    inquiries = Inquiry.objects.select_related("listing", "assigned_to")
    status_counts = {
        row["status"]: row["total"]
        for row in inquiries.values("status").annotate(total=Count("id"))
    }
    active_statuses = [
        Inquiry.Status.NEW,
        Inquiry.Status.CONTACTED,
        Inquiry.Status.QUALIFIED,
        Inquiry.Status.VIEWING,
    ]
    context = {
        "new_count": status_counts.get(Inquiry.Status.NEW, 0),
        "unassigned_count": inquiries.filter(
            assigned_to__isnull=True,
            status__in=active_statuses,
        ).count(),
        "active_count": inquiries.filter(status__in=active_statuses).count(),
        "archived_count": status_counts.get(Inquiry.Status.ARCHIVED, 0),
        "recent_inquiries": inquiries.exclude(status=Inquiry.Status.ARCHIVED)
        .annotate(
            attention_order=Case(
                When(status=Inquiry.Status.NEW, then=Value(0)),
                When(assigned_to__isnull=True, then=Value(1)),
                default=Value(2),
                output_field=IntegerField(),
            )
        )
        .order_by("attention_order", "-created_at")[:12],
        "recent_notes": InquiryNote.objects.select_related("inquiry", "author")[:8],
    }
    return render(request, "inquiries/admin/dashboard.html", context)


@require_admin_access
def inquiry_detail(request, inquiry_id):
    _require_inquiry_access(request.user)
    inquiry = get_object_or_404(
        Inquiry.objects.select_related("listing", "assigned_to"),
        pk=inquiry_id,
    )
    can_view_phone = bool(inquiry.phone) and user_has_sensitive_access(
        user=request.user,
        scope=SensitiveAccessRequest.Scope.PHONE_NUMBER,
    )
    activity = AuditEvent.objects.filter(
        Q(target_type=inquiry._meta.label, target_id=str(inquiry.pk))
        | Q(metadata__inquiry_id=str(inquiry.pk))
    )[:30]
    return render(
        request,
        "inquiries/admin/detail.html",
        {
            "inquiry": inquiry,
            "notes": inquiry.notes.select_related("author"),
            "activity": activity,
            "can_view_phone": can_view_phone,
        },
    )
