from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.utils import timezone


@receiver(user_logged_in)
def record_session_version(sender, request, user, **kwargs):  # noqa: ARG001
    now = int(timezone.now().timestamp())
    request.session["account_session_version"] = user.session_version
    request.session["account_session_started_at"] = now
    request.session["account_session_last_seen_at"] = now
