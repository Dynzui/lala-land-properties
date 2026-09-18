import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django_otp import DEVICE_ID_SESSION_KEY
from django_otp.plugins.otp_totp.models import TOTPDevice

from apps.inquiries.models import Inquiry


pytestmark = pytest.mark.django_db


def verified_login(client, user):
    device = TOTPDevice.objects.create(user=user, name="dashboard-test", confirmed=True)
    client.force_login(user)
    session = client.session
    session[DEVICE_ID_SESSION_KEY] = device.persistent_id
    session["account_session_version"] = user.session_version
    session.save()


def make_staff(role, username):
    user_model = get_user_model()
    return user_model.objects.create_user(
        username=username,
        email=f"{username}@example.test",
        password="safe-test-password",
        role=role,
        status=user_model.Status.ACTIVE,
    )


def test_admin_root_uses_custom_dashboard_with_real_inquiry_count(client):
    user_model = get_user_model()
    owner = make_staff(user_model.Role.OWNER, "dashboard-owner")
    Inquiry.objects.create(
        name="Dashboard Buyer",
        email="buyer@example.test",
        interest=Inquiry.Interest.EXPLORING,
        message="I am looking for a home.",
        consent_given_at=timezone.now(),
    )
    verified_login(client, owner)

    response = client.get(reverse("wagtailadmin_home"))

    assert response.status_code == 200
    assert response.resolver_match.url_name == "lala_cms_dashboard"
    assert response.context["new_inquiry_count"] == 1
    assert b"Welcome back" in response.content
    assert b"Dashboard Buyer" in response.content
    assert b"Add property listing" in response.content
    assert b"Full audit log" in response.content


def test_admin_dashboard_hides_owner_only_links(client):
    user_model = get_user_model()
    admin = make_staff(user_model.Role.ADMIN, "dashboard-admin")
    verified_login(client, admin)

    response = client.get(reverse("lala_cms_dashboard"))

    assert response.status_code == 200
    assert b"Website content" in response.content
    assert b"Staff management" not in response.content
    assert b"Full audit log" not in response.content
