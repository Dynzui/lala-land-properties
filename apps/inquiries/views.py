import hashlib
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.access_requests.models import SensitiveAccessRequest
from apps.access_requests.services import user_has_sensitive_access
from apps.audittrail.models import AuditEvent
from apps.listings.models import Listing

from .forms import PublicInquiryForm
from .models import Inquiry

RATE_LIMIT = 5
RATE_WINDOW_SECONDS = 60 * 60
DUPLICATE_WINDOW_MINUTES = 10


def _rate_key(request) -> str:
    address = request.META.get("REMOTE_ADDR", "unknown")
    digest = hashlib.sha256(address.encode()).hexdigest()
    return f"public-inquiry:{digest}"


def _consume_rate_limit(request) -> bool:
    rate_key = _rate_key(request)
    if cache.add(rate_key, 1, RATE_WINDOW_SECONDS):
        return True
    try:
        return cache.incr(rate_key) <= RATE_LIMIT
    except ValueError:
        cache.set(rate_key, 1, RATE_WINDOW_SECONDS)
        return True


def _recent_duplicate(inquiry):
    return (
        Inquiry.objects.filter(
            created_at__gte=timezone.now() - timedelta(minutes=DUPLICATE_WINDOW_MINUTES),
            listing=inquiry.listing,
            email=inquiry.email,
            phone=inquiry.phone,
            message=inquiry.message,
        )
        .order_by("-created_at")
        .first()
    )


def contact(request):
    listing = None
    listing_id = request.GET.get("listing") or request.POST.get("listing")
    if listing_id:
        listing = Listing.objects.public().filter(pk=listing_id).first()
    initial = {
        "interest": Inquiry.Interest.SPECIFIC if listing else Inquiry.Interest.EXPLORING,
    }
    form = PublicInquiryForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        if not _consume_rate_limit(request):
            form.add_error(None, "Too many recent inquiries. Please try again later.")
        else:
            inquiry = form.save(commit=False)
            inquiry.listing = listing
            inquiry.listing_title_snapshot = listing.title if listing else ""
            inquiry.consent_given_at = timezone.now()
            inquiry.email = inquiry.email.strip().lower()
            inquiry.phone = inquiry.phone.strip()
            inquiry.message = inquiry.message.strip()
            duplicate = _recent_duplicate(inquiry)
            if duplicate is None:
                inquiry.save()
                AuditEvent.objects.create(
                    action="inquiry.submitted",
                    target_type=inquiry._meta.label,
                    target_id=str(inquiry.pk),
                    metadata={"listing_id": str(listing.pk) if listing else None},
                )
            else:
                inquiry = duplicate
                AuditEvent.objects.create(
                    action="inquiry.duplicate_suppressed",
                    target_type=inquiry._meta.label,
                    target_id=str(inquiry.pk),
                )
            request.session["submitted_inquiry_id"] = str(inquiry.pk)
            return redirect("inquiries:success")
    return render(request, "inquiries/contact.html", {"form": form, "listing": listing})


def success(request):
    if not request.session.pop("submitted_inquiry_id", None):
        return redirect("inquiries:contact")
    return render(request, "inquiries/success.html")


@login_required
def phone(request, inquiry_id):
    inquiry = get_object_or_404(Inquiry, pk=inquiry_id)
    if not user_has_sensitive_access(
        user=request.user,
        scope=SensitiveAccessRequest.Scope.PHONE_NUMBER,
    ):
        raise PermissionDenied("Owner approval is required to view customer phone numbers.")
    AuditEvent.objects.create(
        actor=request.user,
        action="inquiry.phone.viewed",
        target_type=inquiry._meta.label,
        target_id=str(inquiry.pk),
    )
    return render(request, "inquiries/phone.html", {"inquiry": inquiry})
