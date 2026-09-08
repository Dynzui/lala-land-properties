import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django_otp import DEVICE_ID_SESSION_KEY
from django_otp.plugins.otp_totp.models import TOTPDevice

from apps.audittrail.models import AuditEvent
from apps.inquiries.models import Inquiry, InquiryNote
from apps.inquiries.services import add_inquiry_note
from apps.listings.admin_forms import GuidedListingForm
from apps.listings.models import Listing
from apps.listings.services import archive_listing, publish_listing, restore_listing
from apps.listings.tests import guided_listing_data, make_catalogue, make_owner

pytestmark = pytest.mark.django_db


def force_verified_login(client, user):
    device = TOTPDevice.objects.create(user=user, name="priority-zero", confirmed=True)
    client.force_login(user)
    session = client.session
    session[DEVICE_ID_SESSION_KEY] = device.persistent_id
    session["account_session_version"] = user.session_version
    session.save()


def make_user(role, username):
    user_model = get_user_model()
    return user_model.objects.create_user(
        username=username,
        email=f"{username}@example.test",
        password="safe-test-password",
        role=role,
        status=user_model.Status.ACTIVE,
    )


def test_priority_zero_role_boundaries_in_admin(client):
    user_model = get_user_model()
    owner = make_user(user_model.Role.OWNER, "p0-owner")
    admin = make_user(user_model.Role.ADMIN, "p0-admin")
    maintainer = make_user(user_model.Role.MAINTAINER, "p0-maintainer")
    customer = make_user(user_model.Role.CUSTOMER, "p0-customer")

    force_verified_login(client, owner)
    owner_response = client.get(reverse("wagtailadmin_home"))
    assert owner_response.status_code == 200
    assert b"Website content" in owner_response.content
    assert b"Staff management" in owner_response.content
    assert b"Audit log" in owner_response.content

    force_verified_login(client, admin)
    admin_response = client.get(reverse("wagtailadmin_home"))
    assert admin_response.status_code == 200
    assert b"Website content" in admin_response.content
    assert b"Staff management" not in admin_response.content
    assert b"Audit log" not in admin_response.content

    for user in (maintainer, customer):
        force_verified_login(client, user)
        response = client.get(reverse("wagtailadmin_home"))
        assert response.status_code == 302
        assert "/account/login/" in response.url


def test_priority_zero_property_to_inquiry_lifecycle(client):
    location, _, property_record = make_catalogue()
    owner = make_owner()
    form = GuidedListingForm(
        data=guided_listing_data(
            location,
            property_record.property_type,
            title="Priority Zero Lifecycle Home",
        )
    )
    assert form.is_valid(), form.errors

    listing = form.save(actor=owner)
    listing = publish_listing(actor=owner, listing=listing)
    public_response = client.get(reverse("listings:detail", args=[listing.slug]))
    assert public_response.status_code == 200
    assert listing.title.encode() in public_response.content

    inquiry_response = client.post(
        reverse("inquiries:contact"),
        {
            "name": "Priority Zero Buyer",
            "email": "priority-zero-buyer@example.test",
            "phone": "09171234567",
            "interest": Inquiry.Interest.SPECIFIC,
            "preferred_location": "Bacolod",
            "budget": "4500000",
            "timeline": "Within six months",
            "message": "I would like to arrange a viewing.",
            "consent": "on",
            "website": "",
            "listing": str(listing.pk),
        },
    )
    assert inquiry_response.status_code == 302
    inquiry = Inquiry.objects.get(email="priority-zero-buyer@example.test")
    assert inquiry.listing == listing

    note = add_inquiry_note(
        actor=owner,
        inquiry=inquiry,
        kind=InquiryNote.Kind.CALL,
        body="Confirmed the buyer's preferred viewing schedule.",
    )
    assert note.author == owner

    listing = archive_listing(actor=owner, listing=listing)
    assert listing.workflow_status == Listing.WorkflowStatus.ARCHIVED
    listing = restore_listing(actor=owner, listing=listing)
    assert listing.workflow_status == Listing.WorkflowStatus.DRAFT

    required_events = {
        "listing.published",
        "inquiry.submitted",
        "inquiry.note.created",
        "listing.archived",
        "listing.restored",
    }
    assert required_events <= set(AuditEvent.objects.values_list("action", flat=True))
