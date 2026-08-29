import hashlib

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied

from apps.accounts.services import (
    accept_staff_invitation,
    create_staff_invitation,
    revoke_staff_invitation,
)
from apps.audittrail.models import AuditEvent

pytestmark = pytest.mark.django_db


def make_user(*, username, role):
    user_model = get_user_model()
    return user_model.objects.create_user(
        username=username,
        email=f"{username}@example.test",
        password="safe-test-password",
        role=role,
        status=user_model.Status.ACTIVE,
    )


def test_owner_can_create_single_use_invitation_without_storing_raw_token():
    user_model = get_user_model()
    owner = make_user(username="owner", role=user_model.Role.OWNER)

    result = create_staff_invitation(
        actor=owner,
        email="New.Admin@Example.test",
        role=user_model.Role.ADMIN,
    )

    assert result.invitation.email == "new.admin@example.test"
    assert result.invitation.token_digest == hashlib.sha256(result.token.encode()).hexdigest()
    assert result.token not in result.invitation.token_digest
    assert result.invitation.is_usable


def test_admin_cannot_invite_staff():
    user_model = get_user_model()
    admin = make_user(username="admin", role=user_model.Role.ADMIN)

    with pytest.raises(PermissionDenied):
        create_staff_invitation(
            actor=admin,
            email="another@example.test",
            role=user_model.Role.ADMIN,
        )


def test_new_invitation_revokes_previous_unused_invitation():
    user_model = get_user_model()
    owner = make_user(username="owner-two", role=user_model.Role.OWNER)
    first = create_staff_invitation(
        actor=owner,
        email="employee@example.test",
        role=user_model.Role.ADMIN,
    )

    create_staff_invitation(
        actor=owner,
        email="employee@example.test",
        role=user_model.Role.ADMIN,
    )

    first.invitation.refresh_from_db()
    assert first.invitation.revoked_at is not None
    assert not first.invitation.is_usable
    assert AuditEvent.objects.filter(
        action="staff.invitation.replaced",
        target_id=str(first.invitation.pk),
    ).exists()


def test_existing_account_email_cannot_be_invited():
    user_model = get_user_model()
    owner = make_user(username="existing-owner", role=user_model.Role.OWNER)
    make_user(username="existing-staff", role=user_model.Role.ADMIN)

    with pytest.raises(ValueError, match="already exists"):
        create_staff_invitation(
            actor=owner,
            email="EXISTING-STAFF@example.test",
            role=user_model.Role.ADMIN,
        )


def test_invitation_can_be_accepted_only_once():
    user_model = get_user_model()
    owner = make_user(username="accepting-owner", role=user_model.Role.OWNER)
    result = create_staff_invitation(
        actor=owner,
        email="employee-accept@example.test",
        role=user_model.Role.ADMIN,
    )

    user = accept_staff_invitation(
        token=result.token,
        password="a-long-and-unusual-test-password-4071",
        full_name="Ana Santos",
    )

    assert user.email == "employee-accept@example.test"
    assert user.role == user_model.Role.ADMIN
    assert user.status == user_model.Status.ACTIVE
    assert user.is_staff
    assert user.first_name == "Ana"
    assert user.last_name == "Santos"
    with pytest.raises(ValueError, match="invalid or has expired"):
        accept_staff_invitation(
            token=result.token,
            password="another-long-and-unusual-test-password-8129",
        )


def test_owner_can_revoke_invitation_and_action_is_audited():
    user_model = get_user_model()
    owner = make_user(username="revoking-owner", role=user_model.Role.OWNER)
    result = create_staff_invitation(
        actor=owner,
        email="revoked@example.test",
        role=user_model.Role.MAINTAINER,
    )

    revoke_staff_invitation(actor=owner, invitation=result.invitation)

    result.invitation.refresh_from_db()
    assert result.invitation.revoked_at is not None
    assert AuditEvent.objects.filter(
        actor=owner,
        action="staff.invitation.revoked",
        target_id=str(result.invitation.pk),
    ).exists()
