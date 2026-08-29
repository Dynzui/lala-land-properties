import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone

pytestmark = pytest.mark.django_db


def test_session_version_mismatch_logs_user_out():
    user_model = get_user_model()
    user = user_model.objects.create_user(
        username="session-user",
        email="session@example.test",
        password="safe-test-password",
        role=user_model.Role.ADMIN,
        status=user_model.Status.ACTIVE,
    )
    client = Client()
    client.force_login(user)
    session = client.session
    session["account_session_version"] = user.session_version
    session.save()

    user.session_version += 1
    user.save(update_fields=["session_version"])

    response = client.get("/admin/")

    assert response.status_code == 302
    assert response.url.startswith("/account/login/")
    assert "_auth_user_id" not in client.session


@pytest.mark.parametrize(
    ("session_key", "age_seconds"),
    [
        ("account_session_last_seen_at", 30 * 60 + 1),
        ("account_session_started_at", 12 * 60 * 60 + 1),
    ],
)
def test_expired_staff_session_is_logged_out(session_key, age_seconds):
    user_model = get_user_model()
    user = user_model.objects.create_user(
        username=f"expired-{session_key}",
        email=f"expired-{session_key}@example.test",
        password="safe-test-password",
        role=user_model.Role.ADMIN,
        status=user_model.Status.ACTIVE,
        is_staff=True,
    )
    client = Client()
    client.force_login(user)
    session = client.session
    session[session_key] = int(timezone.now().timestamp()) - age_seconds
    session.save()

    response = client.get("/admin/")

    assert response.status_code == 302
    assert response.url.startswith("/account/login/")
    assert "_auth_user_id" not in client.session
