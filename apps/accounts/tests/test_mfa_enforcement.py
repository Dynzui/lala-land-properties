import pytest
from django.contrib.auth import get_user_model
from django.test import Client

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("path", ["/admin/", "/django-admin/"])
def test_unverified_staff_are_sent_to_mfa_setup(path):
    user_model = get_user_model()
    user = user_model.objects.create_user(
        username="staff-without-mfa",
        email="staff-without-mfa@example.test",
        password="safe-test-password",
        role=user_model.Role.ADMIN,
        status=user_model.Status.ACTIVE,
        is_staff=True,
    )
    client = Client()
    client.force_login(user)
    session = client.session
    session["account_session_version"] = user.session_version
    session.save()

    response = client.get(path)

    assert response.status_code == 302
    assert response.url == "/account/two_factor/setup/"
