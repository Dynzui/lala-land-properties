import re

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import override_settings
from django.urls import reverse


pytestmark = pytest.mark.django_db


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_admin_password_reset_generates_email_and_branded_flow(client):
    user_model = get_user_model()
    user_model.objects.create_user(
        username="reset-owner",
        email="reset-owner@example.test",
        password="safe-test-password",
        role=user_model.Role.OWNER,
        status=user_model.Status.ACTIVE,
        is_staff=True,
    )

    form_response = client.get(reverse("wagtailadmin_password_reset"))
    assert form_response.status_code == 200
    assert b"Lala Land" in form_response.content
    assert b"Reset your password." in form_response.content

    response = client.post(
        reverse("wagtailadmin_password_reset"),
        {"email": "reset-owner@example.test"},
        follow=True,
    )

    assert response.status_code == 200
    assert response.resolver_match.url_name == "wagtailadmin_password_reset_done"
    assert b"Check your email." in response.content
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["reset-owner@example.test"]
    assert re.search(r"/admin/password_reset/confirm/[^/]+/[^/\s]+/", mail.outbox[0].body)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_admin_password_reset_does_not_reveal_unknown_email(client):
    response = client.post(
        reverse("wagtailadmin_password_reset"),
        {"email": "unknown@example.test"},
        follow=True,
    )

    assert response.status_code == 200
    assert response.resolver_match.url_name == "wagtailadmin_password_reset_done"
    assert b"Check your email." in response.content
    assert mail.outbox == []
