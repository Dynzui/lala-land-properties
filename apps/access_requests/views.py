from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from apps.accounts.capabilities import Capability
from apps.accounts.models import User
from apps.properties.models import Location

from .forms import SensitiveAccessRequestForm, SensitiveAccessReviewForm
from .models import SensitiveAccessGrant, SensitiveAccessRequest
from .services import (
    request_sensitive_access,
    review_sensitive_access,
    revoke_sensitive_access,
    user_has_sensitive_access,
)


@login_required
def access_dashboard(request):
    if request.user.role == User.Role.OWNER:
        access_requests = SensitiveAccessRequest.objects.select_related(
            "requester", "location", "reviewed_by"
        )
        grants = SensitiveAccessGrant.objects.select_related("grantee", "location")
    elif request.user.role == User.Role.ADMIN:
        access_requests = SensitiveAccessRequest.objects.filter(
            requester=request.user
        ).select_related("location", "reviewed_by")
        grants = SensitiveAccessGrant.objects.filter(grantee=request.user).select_related(
            "location"
        )
    else:
        raise PermissionDenied
    return render(
        request,
        "access_requests/dashboard.html",
        {"access_requests": access_requests, "grants": grants},
    )


@login_required
def create_access_request(request):
    if request.user.role != User.Role.ADMIN:
        raise PermissionDenied
    form = SensitiveAccessRequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        request_sensitive_access(
            requester=request.user,
            scope=form.cleaned_data["scope"],
            location=form.cleaned_data.get("location"),
            reason=form.cleaned_data["reason"],
            requested_minutes=form.cleaned_data["requested_minutes"],
        )
        messages.success(request, "Your request was sent to the Owner.")
        return redirect("access_requests:dashboard")
    return render(request, "access_requests/request_form.html", {"form": form})


@login_required
def review_access_request(request, request_id, decision):
    if not request.user.has_capability(Capability.STAFF_MANAGE):
        raise PermissionDenied
    if request.method != "POST" or decision not in {"approve", "deny"}:
        raise PermissionDenied
    access_request = get_object_or_404(SensitiveAccessRequest, pk=request_id)
    form = SensitiveAccessReviewForm(request.POST)
    if form.is_valid():
        review_sensitive_access(
            owner=request.user,
            access_request=access_request,
            approve=decision == "approve",
            review_note=form.cleaned_data["review_note"],
        )
        messages.success(request, f"Access request {decision}d.")
    return redirect("access_requests:dashboard")


@login_required
def revoke_access_grant(request, grant_id):
    if not request.user.has_capability(Capability.STAFF_MANAGE) or request.method != "POST":
        raise PermissionDenied
    grant = get_object_or_404(SensitiveAccessGrant, pk=grant_id)
    revoke_sensitive_access(owner=request.user, grant=grant)
    messages.success(request, "Sensitive access was revoked.")
    return redirect("access_requests:dashboard")


@login_required
def private_location(request, location_id):
    location = get_object_or_404(Location, pk=location_id)
    if not user_has_sensitive_access(
        user=request.user,
        scope=SensitiveAccessRequest.Scope.EXACT_LOCATION,
        location=location,
    ):
        raise PermissionDenied
    return render(
        request,
        "access_requests/private_location.html",
        {"location": location},
    )
