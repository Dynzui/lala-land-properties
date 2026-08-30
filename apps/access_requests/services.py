from datetime import timedelta

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from apps.accounts.capabilities import Capability
from apps.accounts.models import User
from apps.audittrail.models import AuditEvent
from apps.properties.models import Location

from .models import SensitiveAccessGrant, SensitiveAccessRequest


@transaction.atomic
def request_sensitive_access(
    *,
    requester: User,
    scope: str,
    reason: str,
    requested_minutes: int = 60,
    location: Location | None = None,
) -> SensitiveAccessRequest:
    if requester.role != User.Role.ADMIN or requester.status != User.Status.ACTIVE:
        raise PermissionDenied("Only an active Admin may request sensitive access.")
    if not 5 <= requested_minutes <= 24 * 60:
        raise ValueError("Access duration must be between 5 minutes and 24 hours.")
    access_request = SensitiveAccessRequest(
        requester=requester,
        scope=scope,
        reason=reason.strip(),
        requested_minutes=requested_minutes,
        location=location,
    )
    access_request.save()
    AuditEvent.objects.create(
        actor=requester,
        action="sensitive_access.requested",
        target_type=access_request._meta.label,
        target_id=str(access_request.pk),
        metadata={"scope": scope, "location_id": str(location.pk) if location else None},
    )
    return access_request


@transaction.atomic
def review_sensitive_access(
    *,
    owner: User,
    access_request: SensitiveAccessRequest,
    approve: bool,
    review_note: str = "",
) -> SensitiveAccessGrant | None:
    if not owner.has_capability(Capability.STAFF_MANAGE):
        raise PermissionDenied("Only an active Owner may review sensitive access.")
    access_request = SensitiveAccessRequest.objects.select_for_update().get(pk=access_request.pk)
    if access_request.status != SensitiveAccessRequest.Status.PENDING:
        raise ValueError("This access request has already been reviewed.")
    now = timezone.now()
    access_request.status = (
        SensitiveAccessRequest.Status.APPROVED if approve else SensitiveAccessRequest.Status.DENIED
    )
    access_request.reviewed_by = owner
    access_request.reviewed_at = now
    access_request.review_note = review_note.strip()
    access_request.save()
    grant = None
    if approve:
        SensitiveAccessGrant.objects.filter(
            grantee=access_request.requester,
            scope=access_request.scope,
            location=access_request.location,
            revoked_at__isnull=True,
        ).update(revoked_at=now, revoked_by=owner)
        grant = SensitiveAccessGrant.objects.create(
            grantee=access_request.requester,
            scope=access_request.scope,
            location=access_request.location,
            source_request=access_request,
            granted_by=owner,
            expires_at=now + timedelta(minutes=access_request.requested_minutes),
        )
    AuditEvent.objects.create(
        actor=owner,
        action="sensitive_access.approved" if approve else "sensitive_access.denied",
        target_type=access_request._meta.label,
        target_id=str(access_request.pk),
        metadata={"scope": access_request.scope, "grant_id": str(grant.pk) if grant else None},
    )
    return grant


@transaction.atomic
def revoke_sensitive_access(*, owner: User, grant: SensitiveAccessGrant) -> None:
    if not owner.has_capability(Capability.STAFF_MANAGE):
        raise PermissionDenied("Only an active Owner may revoke sensitive access.")
    if grant.revoked_at is None:
        grant.revoked_at = timezone.now()
        grant.revoked_by = owner
        grant.save(update_fields=["revoked_at", "revoked_by"])
        AuditEvent.objects.create(
            actor=owner,
            action="sensitive_access.revoked",
            target_type=grant._meta.label,
            target_id=str(grant.pk),
            metadata={"scope": grant.scope},
        )


def user_has_sensitive_access(*, user: User, scope: str, location: Location | None = None) -> bool:
    owner_capability = (
        Capability.PRIVATE_LOCATION_VIEW
        if scope == SensitiveAccessRequest.Scope.EXACT_LOCATION
        else Capability.PHONE_NUMBER_VIEW
    )
    if user.has_capability(owner_capability):
        return True
    if user.role != User.Role.ADMIN or user.status != User.Status.ACTIVE:
        return False
    return SensitiveAccessGrant.objects.filter(
        grantee=user,
        scope=scope,
        location=location,
        revoked_at__isnull=True,
        expires_at__gt=timezone.now(),
    ).exists()
