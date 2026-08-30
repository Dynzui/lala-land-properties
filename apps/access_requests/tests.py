import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied

from apps.audittrail.models import AuditEvent
from apps.properties.models import Location

from .models import SensitiveAccessRequest
from .services import (
    request_sensitive_access,
    review_sensitive_access,
    revoke_sensitive_access,
    user_has_sensitive_access,
)

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


def make_location():
    return Location.objects.create(
        city_municipality="Bacolod",
        public_label="Bacolod City",
        street_address_private="123 Private Street",
    )


def test_admin_needs_owner_approval_for_exact_location():
    user_model = get_user_model()
    owner = make_user(username="access-owner", role=user_model.Role.OWNER)
    admin = make_user(username="access-admin", role=user_model.Role.ADMIN)
    location = make_location()
    access_request = request_sensitive_access(
        requester=admin,
        scope=SensitiveAccessRequest.Scope.EXACT_LOCATION,
        location=location,
        reason="Arrange an authorized property viewing.",
        requested_minutes=30,
    )

    assert not user_has_sensitive_access(
        user=admin,
        scope=SensitiveAccessRequest.Scope.EXACT_LOCATION,
        location=location,
    )
    grant = review_sensitive_access(owner=owner, access_request=access_request, approve=True)
    assert user_has_sensitive_access(
        user=admin,
        scope=SensitiveAccessRequest.Scope.EXACT_LOCATION,
        location=location,
    )
    assert AuditEvent.objects.filter(action="sensitive_access.approved").exists()

    revoke_sensitive_access(owner=owner, grant=grant)
    assert not user_has_sensitive_access(
        user=admin,
        scope=SensitiveAccessRequest.Scope.EXACT_LOCATION,
        location=location,
    )


def test_admin_cannot_approve_own_request():
    user_model = get_user_model()
    admin = make_user(username="self-approving-admin", role=user_model.Role.ADMIN)
    location = make_location()
    access_request = request_sensitive_access(
        requester=admin,
        scope=SensitiveAccessRequest.Scope.EXACT_LOCATION,
        location=location,
        reason="Need address.",
    )

    with pytest.raises(PermissionDenied):
        review_sensitive_access(owner=admin, access_request=access_request, approve=True)


def test_phone_access_is_revocable_and_not_location_specific():
    user_model = get_user_model()
    owner = make_user(username="phone-owner", role=user_model.Role.OWNER)
    admin = make_user(username="phone-admin", role=user_model.Role.ADMIN)
    access_request = request_sensitive_access(
        requester=admin,
        scope=SensitiveAccessRequest.Scope.PHONE_NUMBER,
        reason="Follow up assigned inquiries.",
    )
    grant = review_sensitive_access(owner=owner, access_request=access_request, approve=True)

    assert user_has_sensitive_access(
        user=admin,
        scope=SensitiveAccessRequest.Scope.PHONE_NUMBER,
    )
    revoke_sensitive_access(owner=owner, grant=grant)
    assert not user_has_sensitive_access(
        user=admin,
        scope=SensitiveAccessRequest.Scope.PHONE_NUMBER,
    )


def test_maintainer_cannot_request_sensitive_access():
    user_model = get_user_model()
    maintainer = make_user(username="access-maintainer", role=user_model.Role.MAINTAINER)

    with pytest.raises(PermissionDenied):
        request_sensitive_access(
            requester=maintainer,
            scope=SensitiveAccessRequest.Scope.PHONE_NUMBER,
            reason="Support request.",
        )
