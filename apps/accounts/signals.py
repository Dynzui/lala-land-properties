from django.contrib.auth.models import Group
from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import User

OWNER_GROUP = "Lala Land Owners"
ADMIN_GROUP = "Lala Land Content Admins"


@receiver(user_logged_in)
def record_session_version(sender, request, user, **kwargs):  # noqa: ARG001
    now = int(timezone.now().timestamp())
    request.session["account_session_version"] = user.session_version
    request.session["account_session_started_at"] = now
    request.session["account_session_last_seen_at"] = now


@receiver(post_save, sender=User)
def sync_wagtail_editor_group(sender, instance, **kwargs):  # noqa: ARG001
    managed_groups = Group.objects.filter(name__in=[OWNER_GROUP, ADMIN_GROUP])
    if not managed_groups.exists():
        return
    instance.groups.remove(*managed_groups)
    target_name = {
        User.Role.OWNER: OWNER_GROUP,
        User.Role.ADMIN: ADMIN_GROUP,
    }.get(instance.role)
    if target_name and instance.status == User.Status.ACTIVE:
        target = managed_groups.filter(name=target_name).first()
        if target:
            instance.groups.add(target)
