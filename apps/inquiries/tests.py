import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import RequestFactory
from django.urls import reverse
from django.utils import timezone
from django_otp import DEVICE_ID_SESSION_KEY
from django_otp.plugins.otp_totp.models import TOTPDevice

from apps.audittrail.models import AuditEvent
from apps.listings.services import publish_listing
from apps.listings.tests import make_catalogue, make_listing, make_offer

from .forms import InquiryAdminForm
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


def force_verified_login(client, user):
    device = TOTPDevice.objects.create(user=user, name="test-device", confirmed=True)
    client.force_login(user)
    session = client.session
    session[DEVICE_ID_SESSION_KEY] = device.persistent_id
    session["account_session_version"] = user.session_version
    session.save()


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


def test_phone_only_submission_is_accepted(client):
    data = inquiry_data(email="", phone="0917 123 4567")

    response = client.post(reverse("inquiries:contact"), data)

    assert response.status_code == 302
    inquiry = Inquiry.objects.get()
    assert inquiry.email == ""
    assert inquiry.phone == "0917 123 4567"


def test_submission_requires_email_or_valid_phone(client):
    response = client.post(reverse("inquiries:contact"), inquiry_data(email="", phone=""))

    assert response.status_code == 200
    assert b"Provide an email address or mobile number" in response.content
    assert not Inquiry.objects.exists()

    response = client.post(
        reverse("inquiries:contact"),
        inquiry_data(email="", phone="123"),
    )
    assert response.status_code == 200
    assert b"Enter a valid mobile number" in response.content
    assert not Inquiry.objects.exists()


def test_recent_duplicate_is_suppressed_and_audited(client):
    data = inquiry_data(email="JUAN@example.test")

    first = client.post(reverse("inquiries:contact"), data)
    second = client.post(reverse("inquiries:contact"), data)

    assert first.status_code == second.status_code == 302
    assert Inquiry.objects.count() == 1
    inquiry = Inquiry.objects.get()
    assert AuditEvent.objects.filter(
        action="inquiry.duplicate_suppressed",
        target_id=str(inquiry.pk),
    ).exists()


def test_listing_inquiry_is_automatically_tagged(client):
    _, variant, property_record = make_catalogue()
    listing = make_listing(property_record=property_record, variant=variant)
    make_offer(listing)
    listing = publish_listing(
        actor=make_user(get_user_model().Role.OWNER, "tag-owner"), listing=listing
    )

    response = client.get(reverse("listings:inquiry", args=[listing.pk]))
    assert response.status_code == 302
    assert f"listing={listing.pk}" in response.url

    response = client.post(
        reverse("inquiries:contact"),
        inquiry_data(listing=str(listing.pk), interest=Inquiry.Interest.SPECIFIC),
    )

    assert response.status_code == 302
    inquiry = Inquiry.objects.get()
    assert inquiry.listing == listing
    assert inquiry.listing_title_snapshot == listing.title


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


def test_cms_note_creation_automatically_uses_signed_in_staff_as_author(client):
    user_model = get_user_model()
    owner = make_user(user_model.Role.OWNER, "cms-note-owner")
    inquiry = Inquiry.objects.create(
        name="CMS Note Lead",
        email="cms-note@example.test",
        interest=Inquiry.Interest.EXPLORING,
        message="Please follow up.",
        consent_given_at=timezone.now(),
    )
    force_verified_login(client, owner)

    response = client.post(
        reverse("wagtailsnippets_inquiries_inquirynote:add"),
        {
            "inquiry": str(inquiry.pk),
            "kind": InquiryNote.Kind.CALL,
            "body": "Called and discussed preferred locations.",
            "occurred_at": timezone.now().strftime("%Y-%m-%d %H:%M"),
        },
    )

    assert response.status_code == 302
    note = InquiryNote.objects.get(inquiry=inquiry)
    assert note.author == owner
    assert AuditEvent.objects.filter(
        action="inquiry.note.created",
        metadata__note_id=str(note.pk),
    ).exists()


def test_inquiry_dashboard_shows_operational_counts_and_masks_phone(client):
    user_model = get_user_model()
    owner = make_user(user_model.Role.OWNER, "dashboard-owner")
    Inquiry.objects.create(
        name="New Lead",
        email="lead@example.test",
        phone="09171234567",
        interest=Inquiry.Interest.EXPLORING,
        message="Please help me find a property.",
        consent_given_at=timezone.now(),
    )
    force_verified_login(client, owner)

    response = client.get(reverse("lala_inquiry_dashboard"))

    assert response.status_code == 200
    assert response.context["new_count"] == 1
    assert response.context["unassigned_count"] == 1
    assert b"New Lead" in response.content
    assert b"4567" in response.content
    assert b"09171234567" not in response.content


def test_inquiry_detail_exposes_phone_only_to_owner_or_approved_admin(client):
    user_model = get_user_model()
    owner = make_user(user_model.Role.OWNER, "detail-owner")
    admin = make_user(user_model.Role.ADMIN, "detail-admin")
    inquiry = Inquiry.objects.create(
        name="Private Contact",
        email="private@example.test",
        phone="09171234567",
        interest=Inquiry.Interest.EXPLORING,
        message="Please contact me.",
        consent_given_at=timezone.now(),
    )

    force_verified_login(client, owner)
    owner_response = client.get(reverse("lala_inquiry_detail", args=[inquiry.pk]))
    assert owner_response.status_code == 200
    assert b"View phone number" in owner_response.content

    force_verified_login(client, admin)
    admin_response = client.get(reverse("lala_inquiry_detail", args=[inquiry.pk]))
    assert admin_response.status_code == 200
    assert b"Request Owner access" in admin_response.content
    assert b"09171234567" not in admin_response.content


def test_assignment_form_only_offers_active_owner_and_admin():
    user_model = get_user_model()
    owner = make_user(user_model.Role.OWNER, "form-owner")
    admin = make_user(user_model.Role.ADMIN, "form-admin")
    make_user(user_model.Role.CUSTOMER, "form-customer")
    suspended = make_user(user_model.Role.ADMIN, "form-suspended")
    suspended.status = user_model.Status.SUSPENDED
    suspended.save()

    form = InquiryAdminForm()

    assert set(form.fields["assigned_to"].queryset) == {owner, admin}


def test_owner_can_open_inquiry_editor_with_restricted_assignment_choices(client):
    user_model = get_user_model()
    owner = make_user(user_model.Role.OWNER, "editor-owner")
    customer = make_user(user_model.Role.CUSTOMER, "editor-customer")
    inquiry = Inquiry.objects.create(
        name="Editable Lead",
        email="editable@example.test",
        interest=Inquiry.Interest.EXPLORING,
        message="I need guidance.",
        consent_given_at=timezone.now(),
    )
    force_verified_login(client, owner)

    response = client.get(reverse("wagtailsnippets_inquiries_inquiry:edit", args=[inquiry.pk]))

    assert response.status_code == 200
    assert owner.email.encode() in response.content
    assert customer.email.encode() not in response.content


def test_archiving_keeps_inquiry_record_and_updates_dashboard(client):
    user_model = get_user_model()
    owner = make_user(user_model.Role.OWNER, "archive-owner")
    inquiry = Inquiry.objects.create(
        name="Archived Lead",
        email="archive@example.test",
        interest=Inquiry.Interest.EXPLORING,
        message="No longer looking.",
        consent_given_at=timezone.now(),
    )

    inquiry = update_inquiry(
        actor=owner,
        inquiry=inquiry,
        status=Inquiry.Status.ARCHIVED,
    )
    force_verified_login(client, owner)
    response = client.get(reverse("lala_inquiry_dashboard"))

    assert Inquiry.objects.filter(pk=inquiry.pk).exists()
    assert inquiry.archived_at is not None
    assert response.context["archived_count"] == 1
    assert b"Archived Lead" not in response.content
