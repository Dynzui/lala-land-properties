import hashlib
import secrets
from dataclasses import dataclass
from datetime import timedelta

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from apps.audittrail.models import AuditEvent

from .capabilities import Capability
from .models import StaffInvitation, User


@dataclass(frozen=True)
class CreatedInvitation:
    invitation: StaffInvitation
    token: str


def _record_event(*, actor: User | None, action: str, target, metadata=None) -> None:
    AuditEvent.objects.create(
        actor=actor,
        action=action,
        target_type=target._meta.label,
        target_id=str(target.pk),
        metadata=metadata or {},
    )


@transaction.atomic
def create_staff_invitation(*, actor: User, email: str, role: str) -> CreatedInvitation:
    if not actor.has_capability(Capability.STAFF_MANAGE):
        raise PermissionDenied("Only an active Owner may invite staff.")
    if role not in {User.Role.ADMIN, User.Role.MAINTAINER}:
        raise ValueError("Staff invitations support Admin or Maintainer roles only.")

    normalized_email = email.strip().lower()
    if User.objects.filter(email__iexact=normalized_email).exists():
        raise ValueError("An account with this email already exists.")

    replaced = list(
        StaffInvitation.objects.select_for_update().filter(
            email__iexact=normalized_email,
            accepted_at__isnull=True,
            revoked_at__isnull=True,
        )
    )
    StaffInvitation.objects.filter(
        pk__in=[invitation.pk for invitation in replaced],
    ).update(revoked_at=timezone.now())
    for invitation in replaced:
        _record_event(
            actor=actor,
            action="staff.invitation.replaced",
            target=invitation,
        )

    token = secrets.token_urlsafe(32)
    invitation = StaffInvitation.objects.create(
        email=normalized_email,
        role=role,
        token_digest=hashlib.sha256(token.encode()).hexdigest(),
        invited_by=actor,
        expires_at=timezone.now() + timedelta(hours=48),
    )
    _record_event(
        actor=actor,
        action="staff.invitation.created",
        target=invitation,
        metadata={"email": invitation.email, "role": invitation.role},
    )
    return CreatedInvitation(invitation=invitation, token=token)


@transaction.atomic
def accept_staff_invitation(*, token: str, password: str, full_name: str = "") -> User:
    digest = hashlib.sha256(token.encode()).hexdigest()
    invitation = StaffInvitation.objects.select_for_update().filter(token_digest=digest).first()
    if invitation is None or not invitation.is_usable:
        raise ValueError("This invitation is invalid or has expired.")

    user = User(
        username=invitation.email,
        email=invitation.email,
        role=invitation.role,
        status=User.Status.ACTIVE,
        is_staff=invitation.role == User.Role.ADMIN,
        is_active=True,
    )
    names = full_name.strip().split(maxsplit=1)
    user.first_name = names[0] if names else ""
    user.last_name = names[1] if len(names) > 1 else ""
    validate_password(password, user=user)
    user.set_password(password)
    user.save()

    invitation.accepted_at = timezone.now()
    invitation.save(update_fields=["accepted_at"])
    _record_event(
        actor=None,
        action="staff.invitation.accepted",
        target=user,
        metadata={"invitation_id": str(invitation.pk), "role": user.role},
    )
    return user


@transaction.atomic
def revoke_staff_invitation(*, actor: User, invitation: StaffInvitation) -> None:
    if not actor.has_capability(Capability.STAFF_MANAGE):
        raise PermissionDenied("Only an active Owner may revoke staff invitations.")
    if invitation.accepted_at is not None:
        raise ValueError("Accepted invitations cannot be revoked.")

    invitation.revoked_at = timezone.now()
    invitation.save(update_fields=["revoked_at"])
    _record_event(actor=actor, action="staff.invitation.revoked", target=invitation)


@transaction.atomic
def change_staff_role(*, actor: User, target: User, role: str) -> None:
    if not actor.has_capability(Capability.STAFF_MANAGE):
        raise PermissionDenied("Only an active Owner may change staff roles.")
    staff_roles = {User.Role.ADMIN, User.Role.MAINTAINER}
    if role not in staff_roles:
        raise ValueError("Staff may only transition between Admin and Maintainer.")
    if target.role not in staff_roles:
        raise ValueError("Owner and Customer roles cannot be changed through staff management.")

    target.role = role
    target.is_staff = role == User.Role.ADMIN
    target.session_version += 1
    target.save(update_fields=["role", "is_staff", "session_version"])
    _record_event(
        actor=actor,
        action="staff.role.changed",
        target=target,
        metadata={"role": role},
    )


@transaction.atomic
def change_account_status(*, actor: User, target: User, status: str) -> None:
    if not actor.has_capability(Capability.STAFF_MANAGE):
        raise PermissionDenied("Only an active Owner may change staff access.")
    if status not in {User.Status.ACTIVE, User.Status.SUSPENDED, User.Status.DISABLED}:
        raise ValueError("Unknown account status.")
    if target.pk == actor.pk and status != User.Status.ACTIVE:
        raise ValueError("Owners cannot suspend or disable themselves.")

    target.status = status
    target.disabled_at = timezone.now() if status == User.Status.DISABLED else None
    target.is_active = status == User.Status.ACTIVE
    target.session_version += 1
    target.save(update_fields=["status", "disabled_at", "is_active", "session_version"])
    _record_event(
        actor=actor,
        action="staff.status.changed",
        target=target,
        metadata={"status": status},
    )
