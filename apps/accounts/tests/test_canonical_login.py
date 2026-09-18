import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse


pytestmark = pytest.mark.django_db


def test_wagtail_login_redirects_to_two_factor_login(client):
    response = client.get("/admin/login/?next=/admin/audit-log/")

    assert response.status_code == 302
    assert response.url == "/account/login/?next=%2Fadmin%2Faudit-log%2F"


def test_two_factor_login_uses_lala_branding(client):
    response = client.get(reverse("two_factor:login"))

    assert response.status_code == 200
    assert b"Lala Land" in response.content
    assert b"Welcome back." in response.content
    assert b"Provide a template named" not in response.content


def test_first_login_requests_credentials_once_then_starts_mfa_setup(client):
    user_model = get_user_model()
    user_model.objects.create_user(
        username="new-mfa-admin",
        email="new-mfa-admin@example.test",
        password="safe-test-password",
        role=user_model.Role.ADMIN,
        status=user_model.Status.ACTIVE,
        is_staff=True,
    )

    response = client.post(
        f"{reverse('two_factor:login')}?next=/admin/",
        {
            "login_view-current_step": "auth",
            "auth-username": "new-mfa-admin",
            "auth-password": "safe-test-password",
        },
    )

    assert response.status_code == 302
    assert response.url == "/admin/"
    assert client.session.get("_auth_user_id") is not None

    admin_response = client.get(response.url)
    assert admin_response.status_code == 302
    assert admin_response.url == reverse("two_factor:setup")


def test_password_reset_returns_to_canonical_login(client):
    response = client.get(reverse("wagtailadmin_password_reset"))

    assert response.status_code == 200
    assert reverse("two_factor:login").encode() in response.content
