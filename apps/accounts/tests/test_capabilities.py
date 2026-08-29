import pytest
from django.contrib.auth import get_user_model

from apps.accounts.capabilities import Capability

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    ("role", "allowed", "denied"),
    [
        ("OWNER", Capability.STAFF_MANAGE, None),
        ("ADMIN", Capability.ARTICLE_MANAGE, Capability.STAFF_MANAGE),
        ("MAINTAINER", Capability.TECHNICAL_MAINTAIN, Capability.INQUIRY_MANAGE),
        ("CUSTOMER", None, Capability.LISTING_MANAGE),
    ],
)
def test_role_capabilities(role, allowed, denied):
    user_model = get_user_model()
    user = user_model.objects.create_user(
        username=f"test-{role.lower()}",
        email=f"{role.lower()}@example.test",
        password="safe-test-password",
        role=role,
        status=user_model.Status.ACTIVE,
    )

    if allowed:
        assert user.has_capability(allowed)
    if denied:
        assert not user.has_capability(denied)


def test_suspended_owner_has_no_capabilities():
    user_model = get_user_model()
    user = user_model.objects.create_user(
        username="suspended-owner",
        email="suspended@example.test",
        password="safe-test-password",
        role=user_model.Role.OWNER,
        status=user_model.Status.SUSPENDED,
    )

    assert not user.has_capability(Capability.STAFF_MANAGE)
