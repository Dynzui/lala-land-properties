from django.core.exceptions import PermissionDenied
from django.db.models import Case, IntegerField, Value, When
from django.shortcuts import render
from django.urls import reverse
from wagtail.admin.auth import require_admin_access

from apps.accounts.capabilities import Capability
from apps.inquiries.models import Inquiry
from apps.listings.models import Listing
from apps.media_library.models import CatalogueMedia


ACTIVE_INQUIRY_STATUSES = [
    Inquiry.Status.NEW,
    Inquiry.Status.CONTACTED,
    Inquiry.Status.QUALIFIED,
    Inquiry.Status.VIEWING,
]


def _draft_listing_rows():
    listings = (
        Listing.objects.filter(workflow_status=Listing.WorkflowStatus.DRAFT)
        .select_related("property", "variant")
        .prefetch_related("offers", "property__media", "variant__media")
        .order_by("-updated_at")[:8]
    )
    rows = []
    for listing in listings:
        reasons = []
        if not any(offer.active for offer in listing.offers.all()):
            reasons.append("Add a price")
        target = listing.property or listing.variant
        media = target.media.all() if target else []
        if not any(
            item.kind == CatalogueMedia.Kind.PHOTO and item.archived_at is None
            for item in media
        ):
            reasons.append("Add a photo")
        rows.append(
            {
                "listing": listing,
                "reason": " · ".join(reasons) if reasons else "Ready to review",
                "url": reverse("lala_guided_listing_edit", args=[listing.pk]),
            }
        )
    return rows[:5]


def _recent_activity(can_manage_inquiries, can_manage_listings):
    activity = []
    if can_manage_inquiries:
        for inquiry in Inquiry.objects.select_related("listing").order_by("-created_at")[:5]:
            activity.append(
                {
                    "title": f"New inquiry from {inquiry.name}",
                    "description": inquiry.property_reference,
                    "timestamp": inquiry.created_at,
                    "url": reverse("lala_inquiry_detail", args=[inquiry.pk]),
                }
            )
    if can_manage_listings:
        for listing in Listing.objects.order_by("-updated_at")[:5]:
            activity.append(
                {
                    "title": f"{listing.title} was updated",
                    "description": listing.get_workflow_status_display(),
                    "timestamp": listing.updated_at,
                    "url": reverse("lala_guided_listing_edit", args=[listing.pk]),
                }
            )
    return sorted(activity, key=lambda item: item["timestamp"], reverse=True)[:6]


@require_admin_access
def cms_dashboard(request):
    can_manage_inquiries = request.user.has_capability(Capability.INQUIRY_MANAGE)
    can_manage_listings = request.user.has_capability(Capability.LISTING_MANAGE)
    can_manage_content = request.user.has_capability(Capability.ARTICLE_MANAGE)
    can_manage_staff = request.user.has_capability(Capability.STAFF_MANAGE)
    if not any((can_manage_inquiries, can_manage_listings, can_manage_content)):
        raise PermissionDenied

    inquiries = Inquiry.objects.all()
    listings = Listing.objects.all()
    context = {
        "can_manage_inquiries": can_manage_inquiries,
        "can_manage_listings": can_manage_listings,
        "can_manage_content": can_manage_content,
        "can_manage_staff": can_manage_staff,
        "new_inquiry_count": (
            inquiries.filter(status=Inquiry.Status.NEW).count() if can_manage_inquiries else 0
        ),
        "unassigned_inquiry_count": (
            inquiries.filter(
                assigned_to__isnull=True,
                status__in=ACTIVE_INQUIRY_STATUSES,
            ).count()
            if can_manage_inquiries
            else 0
        ),
        "draft_listing_count": (
            listings.filter(workflow_status=Listing.WorkflowStatus.DRAFT).count()
            if can_manage_listings
            else 0
        ),
        "published_listing_count": (
            listings.filter(workflow_status=Listing.WorkflowStatus.PUBLISHED).count()
            if can_manage_listings
            else 0
        ),
        "available_listing_count": (
            listings.filter(
                workflow_status=Listing.WorkflowStatus.PUBLISHED,
                public_status=Listing.PublicStatus.AVAILABLE,
            ).count()
            if can_manage_listings
            else 0
        ),
        "attention_inquiries": (
            inquiries.filter(status__in=ACTIVE_INQUIRY_STATUSES)
            .select_related("listing", "assigned_to")
            .annotate(
                attention_order=Case(
                    When(status=Inquiry.Status.NEW, then=Value(0)),
                    When(assigned_to__isnull=True, then=Value(1)),
                    default=Value(2),
                    output_field=IntegerField(),
                )
            )
            .order_by("attention_order", "-created_at")[:5]
            if can_manage_inquiries
            else []
        ),
        "attention_listings": _draft_listing_rows() if can_manage_listings else [],
        "recent_activity": _recent_activity(can_manage_inquiries, can_manage_listings),
    }
    return render(request, "dashboard/admin/home.html", context)
