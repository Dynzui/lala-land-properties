import pytest
from django.contrib.auth import get_user_model

from apps.accounts.services import change_account_status, change_staff_role
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


def test_role_change_revokes_sessions_and_is_audited():
    user_model = get_user_model()
    owner = make_user(username="role-owner", role=user_model.Role.OWNER)
    admin = make_user(username="role-admin", role=user_model.Role.ADMIN)
    previous_version = admin.session_version

    change_staff_role(actor=owner, target=admin, role=user_model.Role.MAINTAINER)

    admin.refresh_from_db()
    assert admin.role == user_model.Role.MAINTAINER
    assert not admin.is_staff
    assert admin.session_version == previous_version + 1
    assert AuditEvent.objects.filter(
        action="staff.role.changed",
        target_id=str(admin.pk),
    ).exists()


def test_suspension_revokes_sessions_and_is_audited():
    user_model = get_user_model()
    owner = make_user(username="status-owner", role=user_model.Role.OWNER)
    admin = make_user(username="status-admin", role=user_model.Role.ADMIN)

    change_account_status(actor=owner, target=admin, status=user_model.Status.SUSPENDED)

    admin.refresh_from_db()
    assert admin.status == user_model.Status.SUSPENDED
    assert not admin.is_active
    assert admin.session_version == 2
    assert AuditEvent.objects.filter(
        action="staff.status.changed", target_id=str(admin.pk)
    ).exists()


def test_owner_cannot_disable_self():
    user_model = get_user_model()
    owner = make_user(username="self-owner", role=user_model.Role.OWNER)

    with pytest.raises(ValueError, match="cannot suspend or disable"):
        change_account_status(actor=owner, target=owner, status=user_model.Status.DISABLED)


def test_owner_role_cannot_be_changed_through_staff_management():
    user_model = get_user_model()
    owner = make_user(username="protected-owner", role=user_model.Role.OWNER)

    with pytest.raises(ValueError, match="cannot be changed"):
        change_staff_role(actor=owner, target=owner, role=user_model.Role.ADMIN)


def test_staff_cannot_be_promoted_to_owner_through_staff_management():
    user_model = get_user_model()
    owner = make_user(username="promotion-owner", role=user_model.Role.OWNER)
    admin = make_user(username="promotion-admin", role=user_model.Role.ADMIN)

    with pytest.raises(ValueError, match="Admin and Maintainer"):
        change_staff_role(actor=owner, target=admin, role=user_model.Role.OWNER)
