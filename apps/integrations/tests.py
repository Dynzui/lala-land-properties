import smtplib

import pytest
from django.core import mail
from django.urls import reverse

from apps.audittrail.models import AuditEvent
from apps.inquiries.models import Inquiry
from apps.sitecontent.models import SiteContactSettings

from .models import InquiryNotification

pytestmark = pytest.mark.django_db


def inquiry_data(**overrides):
    data = {
        "name": "Notification Test Buyer",
        "email": "buyer@example.test",
        "phone": "+63 917 123 4567",
        "interest": Inquiry.Interest.FIRST_HOME,
        "preferred_location": "Bacolod",
        "budget": "3000000",
        "timeline": "Within six months",
        "message": "Please help me find a home.",
        "consent": "on",
        "website": "",
    }
    data.update(overrides)
    return data


def configure_recipient(email="owner@example.test"):
    contact_settings = SiteContactSettings.objects.get(pk=1)
    contact_settings.inquiry_notification_email = email
    contact_settings.save()


def test_new_inquiry_sends_one_private_cms_alert(client):
    configure_recipient()

    response = client.post(reverse("inquiries:contact"), inquiry_data())

    assert response.status_code == 302
    inquiry = Inquiry.objects.get()
    notification = InquiryNotification.objects.get(inquiry=inquiry)
    assert notification.status == InquiryNotification.Status.SENT
    assert notification.recipient == "owner@example.test"
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["owner@example.test"]
    assert reverse("lala_inquiry_detail", args=[inquiry.pk]) in mail.outbox[0].body
    assert inquiry.phone not in mail.outbox[0].body
    assert AuditEvent.objects.filter(
        action="inquiry.notification_sent",
        target_id=str(inquiry.pk),
    ).exists()


def test_duplicate_submission_does_not_send_duplicate_alert(client):
    configure_recipient()
    data = inquiry_data()

    client.post(reverse("inquiries:contact"), data)
    client.post(reverse("inquiries:contact"), data)

    assert Inquiry.objects.count() == 1
    assert InquiryNotification.objects.count() == 1
    assert len(mail.outbox) == 1


def test_email_failure_is_logged_without_losing_inquiry(client, monkeypatch):
    configure_recipient()

    def fail_delivery(*args, **kwargs):
        raise smtplib.SMTPException("Test delivery failure")

    monkeypatch.setattr("apps.integrations.services.send_mail", fail_delivery)

    response = client.post(reverse("inquiries:contact"), inquiry_data())

    assert response.status_code == 302
    inquiry = Inquiry.objects.get()
    notification = InquiryNotification.objects.get(inquiry=inquiry)
    assert notification.status == InquiryNotification.Status.FAILED
    assert notification.error_type == "SMTPException"
    assert AuditEvent.objects.filter(
        action="inquiry.notification_failed",
        target_id=str(inquiry.pk),
        metadata__error_type="SMTPException",
    ).exists()


def test_blank_recipient_disables_alerts(client):
    response = client.post(reverse("inquiries:contact"), inquiry_data())

    assert response.status_code == 302
    assert Inquiry.objects.exists()
    assert not InquiryNotification.objects.exists()
    assert len(mail.outbox) == 0
