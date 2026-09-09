import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django_otp import DEVICE_ID_SESSION_KEY
from django_otp.plugins.otp_totp.models import TOTPDevice
from wagtail.images import get_image_model
from wagtail.images.tests.utils import get_test_image_file

from apps.audittrail.models import AuditEvent
from apps.inquiries.models import Inquiry, InquiryNote
from apps.inquiries.services import add_inquiry_note
from apps.listings.admin_forms import GuidedListingForm
from apps.listings.models import Listing, Offer
from apps.listings.services import archive_listing, publish_listing, restore_listing
from apps.listings.tests import guided_listing_data, make_catalogue, make_owner
from apps.media_library.models import CatalogueMedia
from apps.properties.models import Development, Location, Property

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


def test_owner_primary_cms_routes_are_healthy(client):
    user_model = get_user_model()
    owner = make_user(user_model.Role.OWNER, "cms-smoke-owner")
    force_verified_login(client, owner)
    route_names = [
        "wagtailadmin_home",
        "lala_content_dashboard",
        "lala_listing_workflow",
        "wagtailsnippets_properties_development:list",
        "lala_inquiry_dashboard",
        "lala_staff_dashboard",
        "lala_audit_log",
        "wagtailsnippets_sitecontent_articlecategory:list",
        "wagtailsnippets_sitecontent_sitecontactsettings:list",
    ]

    for route_name in route_names:
        response = client.get(reverse(route_name))
        assert response.status_code == 200, route_name


def test_admin_primary_cms_routes_and_owner_boundaries_are_healthy(client):
    user_model = get_user_model()
    admin = make_user(user_model.Role.ADMIN, "cms-smoke-admin")
    force_verified_login(client, admin)
    allowed_routes = [
        "wagtailadmin_home",
        "lala_content_dashboard",
        "lala_listing_workflow",
        "wagtailsnippets_properties_development:list",
        "lala_inquiry_dashboard",
        "wagtailsnippets_sitecontent_articlecategory:list",
    ]
    owner_only_routes = [
        "lala_staff_dashboard",
        "lala_audit_log",
        "wagtailsnippets_sitecontent_sitecontactsettings:list",
    ]

    for route_name in allowed_routes:
        response = client.get(reverse(route_name))
        assert response.status_code == 200, route_name
    for route_name in owner_only_routes:
        response = client.get(reverse(route_name))
        assert response.status_code in {302, 403}, route_name


def test_priority_zero_property_to_inquiry_lifecycle(client):
    location, _, seed_property = make_catalogue()
    owner = make_owner()
    form = GuidedListingForm(
        data=guided_listing_data(
            location,
            seed_property.property_type,
            title="Priority Zero Lifecycle Home",
        )
    )
    assert form.is_valid(), form.errors

    listing = form.save(actor=owner)
    property_record = listing.property
    image_model = get_image_model()
    photo = CatalogueMedia.objects.create(
        image=image_model.objects.create(
            title="Lifecycle exterior",
            file=get_test_image_file(filename="lifecycle-exterior.png"),
        ),
        property=property_record,
        alt_text="Front exterior of the lifecycle test home",
        is_cover=True,
    )
    floor_plan = CatalogueMedia.objects.create(
        image=image_model.objects.create(
            title="Lifecycle floor plan",
            file=get_test_image_file(filename="lifecycle-floor-plan.png"),
        ),
        property=property_record,
        kind=CatalogueMedia.Kind.FLOOR_PLAN,
        alt_text="Floor plan of the lifecycle test home",
    )

    listing = publish_listing(actor=owner, listing=listing)
    public_response = client.get(reverse("listings:detail", args=[listing.slug]))
    assert public_response.status_code == 200
    assert listing.title.encode() in public_response.content
    assert public_response.context["gallery"] == [photo]
    assert public_response.context["floor_plans"] == [floor_plan]

    listing_count = Listing.objects.count()
    property_count = Property.objects.count()
    offer_count = Offer.objects.count()
    edit_form = GuidedListingForm(
        data=guided_listing_data(
            location,
            seed_property.property_type,
            title="Updated Priority Zero Lifecycle Home",
            summary="An edited customer-facing summary.",
            bedrooms="4",
            price_min="4650000",
        ),
        listing=listing,
    )
    assert edit_form.is_valid(), edit_form.errors
    listing = edit_form.save(actor=owner)
    listing.property.refresh_from_db()
    assert listing.title == "Updated Priority Zero Lifecycle Home"
    assert listing.property.bedrooms == 4
    assert listing.offers.get(active=True).price_min == 4_650_000
    assert Listing.objects.count() == listing_count
    assert Property.objects.count() == property_count
    assert Offer.objects.count() == offer_count
    assert Location.objects.filter(pk=location.pk).exists()
    assert Development.objects.filter(pk=seed_property.development_id).exists()

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
    archived_response = client.get(reverse("listings:detail", args=[listing.slug]))
    assert archived_response.status_code == 200
    assert b"currently unavailable" in archived_response.content
    listing = restore_listing(actor=owner, listing=listing)
    assert listing.workflow_status == Listing.WorkflowStatus.DRAFT
    draft_response = client.get(reverse("listings:detail", args=[listing.slug]))
    assert draft_response.status_code == 200
    assert b"currently unavailable" in draft_response.content
    listing = publish_listing(actor=owner, listing=listing)
    restored_response = client.get(reverse("listings:detail", args=[listing.slug]))
    assert restored_response.status_code == 200
    assert listing.title.encode() in restored_response.content
    assert restored_response.context["gallery"] == [photo]
    assert restored_response.context["floor_plans"] == [floor_plan]

    required_events = {
        "catalogue.property.created",
        "catalogue.property.updated",
        "listing.record.created",
        "listing.record.updated",
        "listing.published",
        "inquiry.submitted",
        "inquiry.note.created",
        "listing.archived",
        "listing.restored",
    }
    assert required_events <= set(AuditEvent.objects.values_list("action", flat=True))
