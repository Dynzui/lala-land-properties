from django.conf import settings
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone

from .models import User


class ActiveAccountMiddleware:
    """Reject inactive staff and sessions invalidated by a security change."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        if user.is_authenticated:
            session_version = request.session.get("account_session_version")
            now = int(timezone.now().timestamp())
            started_at = request.session.get("account_session_started_at")
            last_seen_at = request.session.get("account_session_last_seen_at")
            idle_expired = (
                last_seen_at is None or now - last_seen_at > settings.ACCOUNT_SESSION_IDLE_SECONDS
            )
            absolute_expired = (
                started_at is None or now - started_at > settings.ACCOUNT_SESSION_ABSOLUTE_SECONDS
            )
            invalid = (
                user.status != User.Status.ACTIVE
                or not user.is_active
                or session_version != user.session_version
                or idle_expired
                or absolute_expired
            )
            if invalid:
                logout(request)
                return redirect("two_factor:login")
            request.session["account_session_last_seen_at"] = now
        return self.get_response(request)


class StaffMFARequiredMiddleware:
    """Require a verified OTP device before either administration surface."""

    protected_prefixes = ("/admin/", "/django-admin/", "/staff/")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        is_protected = request.path.startswith(self.protected_prefixes)
        is_verified = getattr(user, "is_verified", lambda: False)()

        if user.is_authenticated and is_protected and not is_verified:
            return redirect(reverse("two_factor:setup"))

        return self.get_response(request)
