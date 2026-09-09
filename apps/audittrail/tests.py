import pytest

from apps.accounts.admin_views import _audit_entries
from apps.audittrail.models import AuditEvent

pytestmark = pytest.mark.django_db


def test_audit_events_cannot_be_changed_or_deleted():
    event = AuditEvent.objects.create(
        action="test.created",
        target_type="tests.Target",
        target_id="one",
    )
    event.action = "test.changed"

    with pytest.raises(TypeError, match="immutable"):
        event.save()
    with pytest.raises(TypeError, match="cannot be deleted"):
        event.delete()
    with pytest.raises(TypeError, match="immutable"):
        AuditEvent.objects.filter(pk=event.pk).update(action="test.changed")
    with pytest.raises(TypeError, match="cannot be deleted"):
        AuditEvent.objects.filter(pk=event.pk).delete()


@pytest.mark.parametrize(
    ("notification_action", "expected_status", "expected_tone"),
    [
        ("inquiry.notification_sent", "Email notification sent", "success"),
        ("inquiry.notification_failed", "Email notification failed", "critical"),
    ],
)
def test_inquiry_submission_and_notification_are_grouped_for_display(
    notification_action,
    expected_status,
    expected_tone,
):
    inquiry_id = "7496d05f-c1c0-4668-9064-15a27b360adf"
    AuditEvent.objects.create(
        action="inquiry.submitted",
        target_type="inquiries.Inquiry",
        target_id=inquiry_id,
    )
    AuditEvent.objects.create(
        action=notification_action,
        target_type="inquiries.Inquiry",
        target_id=inquiry_id,
    )

    entries = _audit_entries(AuditEvent.objects.all())

    assert len(entries) == 1
    assert entries[0]["title"] == "New inquiry received"
    assert entries[0]["status"] == expected_status
    assert entries[0]["status_tone"] == expected_tone
    assert entries[0]["record_url"].endswith(f"/admin/inquiries/{inquiry_id}/")


def test_unrelated_audit_events_remain_separate():
    AuditEvent.objects.create(
        action="listing.published",
        target_type="listings.Listing",
        target_id="listing-one",
    )
    AuditEvent.objects.create(
        action="site.contact_settings.updated",
        target_type="sitecontent.SiteContactSettings",
        target_id="1",
    )

    entries = _audit_entries(AuditEvent.objects.all())

    assert [entry["title"] for entry in entries] == [
        "Contact settings updated",
        "Listing published",
    ]
    assert entries[0]["record_label"] == "Contact settings"
