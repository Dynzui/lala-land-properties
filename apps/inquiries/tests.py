import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import RequestFactory
from django.urls import reverse
from django.utils import timezone

from apps.audittrail.models import AuditEvent

from .models import Inquiry, InquiryNote
from .services import add_inquiry_note, update_inquiry
from .views import phone

pytestmark = pytest.mark.django_db


def make_user(role, username):
    user_model = get_user_model()
    return user_model.objects.create_user(
        username=username,
        email=f"{username}@example.test",
        password="safe-test-password",
        role=role,
        status=user_model.Status.ACTIVE,
    )


def inquiry_data(**overrides):
    values = {
        "name": "Juan Dela Cruz",
        "email": "juan@example.test",
        "phone": "+63 917 123 4567",
        "interest": Inquiry.Interest.FIRST_HOME,
        "preferred_location": "Bacolod",
        "budget": "PHP 3–5M",
        "timeline": "Within six months",
        "message": "I would like help finding a home.",
        "consent": "on",
        "website": "",
    }
    values.update(overrides)
    return values


@pytest.fixture(autouse=True)
def clear_rate_limit_cache():
    cache.clear()


def test_public_submission_requires_consent_and_creates_audited_record(client):
    response = client.post(reverse("inquiries:contact"), inquiry_data())

    inquiry = Inquiry.objects.get()
    assert response.status_code == 302
    assert response.url == reverse("inquiries:success")
    assert inquiry.email == "juan@example.test"
    assert inquiry.consent_given_at is not None
    assert AuditEvent.objects.filter(action="inquiry.submitted", target_id=str(inquiry.pk)).exists()

    missing_consent = inquiry_data(email="other@example.test")
    missing_consent.pop("consent")
    response = client.post(reverse("inquiries:contact"), missing_consent)
    assert response.status_code == 200
    assert Inquiry.objects.count() == 1


def test_honeypot_rejects_bot_submission(client):
    response = client.post(reverse("inquiries:contact"), inquiry_data(website="spam.test"))

    assert response.status_code == 200
    assert not Inquiry.objects.exists()


def test_rate_limit_rejects_sixth_submission(client):
    for index in range(6):
        response = client.post(
            reverse("inquiries:contact"),
            inquiry_data(email=f"person-{index}@example.test"),
            REMOTE_ADDR="203.0.113.10",
        )

    assert Inquiry.objects.count() == 5
    assert response.status_code == 200
    assert b"Too many recent inquiries" in response.content


def test_only_owner_or_approved_admin_can_view_phone():
    user_model = get_user_model()
    owner = make_user(user_model.Role.OWNER, "inquiry-owner")
    admin = make_user(user_model.Role.ADMIN, "inquiry-admin")
    inquiry = Inquiry.objects.create(
        name="Buyer",
        email="buyer@example.test",
        phone="09171234567",
        interest=Inquiry.Interest.EXPLORING,
        message="Please call me.",
        consent_given_at=timezone.now(),
    )
    factory = RequestFactory()
    owner_request = factory.get("/")
    owner_request.user = owner
    response = phone(owner_request, inquiry.pk)
    assert response.status_code == 200

    admin_request = factory.get("/")
    admin_request.user = admin
    with pytest.raises(PermissionDenied):
        phone(admin_request, inquiry.pk)


def test_assignment_rejects_customer_and_status_changes_are_audited():
    user_model = get_user_model()
    owner = make_user(user_model.Role.OWNER, "assignment-owner")
    customer = make_user(user_model.Role.CUSTOMER, "assignment-customer")
    inquiry = Inquiry.objects.create(
        name="Buyer",
        email="buyer@example.test",
        interest=Inquiry.Interest.EXPLORING,
        message="Help requested.",
        consent_given_at=timezone.now(),
    )
    inquiry.assigned_to = customer
    with pytest.raises(ValidationError, match="active Owner or Admin"):
        inquiry.save()

    inquiry = update_inquiry(
        actor=owner,
        inquiry=inquiry,
        status=Inquiry.Status.CONTACTED,
        assigned_to=owner,
    )
    assert inquiry.status == Inquiry.Status.CONTACTED
    assert AuditEvent.objects.filter(action="inquiry.updated").exists()


def test_internal_note_records_author_and_audit_event():
    user_model = get_user_model()
    owner = make_user(user_model.Role.OWNER, "note-owner")
    inquiry = Inquiry.objects.create(
        name="Buyer",
        email="buyer@example.test",
        interest=Inquiry.Interest.EXPLORING,
        message="Help requested.",
        consent_given_at=timezone.now(),
    )

    note = add_inquiry_note(
        actor=owner,
        inquiry=inquiry,
        kind=InquiryNote.Kind.CALL,
        body="Discussed preferred locations.",
    )

    assert note.author == owner
    assert AuditEvent.objects.filter(action="inquiry.note.created").exists()
