import pytest
from django.contrib.auth import authenticate, get_user_model
from django.db import IntegrityError

pytestmark = pytest.mark.django_db


def create_user(*, username, role, status=None, is_active=True):
    user_model = get_user_model()
    return user_model.objects.create_user(
        username=username,
        email=f"{username}@example.test",
        password="safe-test-password",
        role=role,
        status=status or user_model.Status.ACTIVE,
        is_active=is_active,
    )


def test_customer_authentication_is_disabled_for_v1():
    user_model = get_user_model()
    create_user(username="customer-login", role=user_model.Role.CUSTOMER)

    assert authenticate(username="customer-login", password="safe-test-password") is None


@pytest.mark.parametrize("status", ["SUSPENDED", "DISABLED"])
def test_non_active_account_cannot_authenticate(status):
    user_model = get_user_model()
    create_user(username=f"blocked-{status.lower()}", role=user_model.Role.ADMIN, status=status)

    assert (
        authenticate(
            username=f"blocked-{status.lower()}",
            password="safe-test-password",
        )
        is None
    )


def test_account_status_is_kept_in_sync_with_django_is_active():
    user_model = get_user_model()
    user = create_user(username="sync-status", role=user_model.Role.ADMIN)

    user.status = user_model.Status.SUSPENDED
    user.save(update_fields=["status"])

    user.refresh_from_db()
    assert not user.is_active


def test_email_is_case_insensitively_unique():
    user_model = get_user_model()
    create_user(username="case-one", role=user_model.Role.ADMIN)

    with pytest.raises(IntegrityError):
        user_model.objects.create_user(
            username="case-two",
            email="CASE-ONE@EXAMPLE.TEST",
            password="safe-test-password",
            role=user_model.Role.ADMIN,
            status=user_model.Status.ACTIVE,
        )


def test_only_owner_and_admin_receive_wagtail_admin_permission():
    user_model = get_user_model()
    owner = create_user(username="permission-owner", role=user_model.Role.OWNER)
    admin = create_user(username="permission-admin", role=user_model.Role.ADMIN)
    maintainer = create_user(username="permission-maintainer", role=user_model.Role.MAINTAINER)

    assert owner.has_perm("wagtailadmin.access_admin")
    assert admin.has_perm("wagtailadmin.access_admin")
    assert not maintainer.has_perm("wagtailadmin.access_admin")


def test_property_permissions_keep_private_locations_owner_only():
    user_model = get_user_model()
    owner = create_user(username="property-owner", role=user_model.Role.OWNER)
    admin = create_user(username="property-admin", role=user_model.Role.ADMIN)

    assert owner.has_perm("properties.change_location")
    assert admin.has_perm("properties.view_location")
    assert not admin.has_perm("properties.change_location")
    assert owner.has_perm("properties.change_property")
    assert admin.has_perm("properties.change_property")
    assert not owner.has_perm("properties.delete_property")
