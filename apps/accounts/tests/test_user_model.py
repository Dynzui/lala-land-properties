import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

pytestmark = pytest.mark.django_db


def test_user_uses_uuid_primary_key():
    user = get_user_model().objects.create_user(
        username="lala",
        email="lala@example.test",
        password="safe-test-password",
        role=get_user_model().Role.OWNER,
        status=get_user_model().Status.ACTIVE,
    )

    assert user.pk.version == 4
    assert user.role == get_user_model().Role.OWNER


def test_email_is_unique():
    user_model = get_user_model()
    user_model.objects.create_user(
        username="first",
        email="shared@example.test",
        password="safe-test-password",
        role=user_model.Role.ADMIN,
    )

    with pytest.raises(IntegrityError):
        user_model.objects.create_user(
            username="second",
            email="shared@example.test",
            password="safe-test-password",
            role=user_model.Role.ADMIN,
        )
