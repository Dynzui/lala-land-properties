from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse
from django.utils import timezone

from apps.audittrail.models import AuditEvent
from apps.sitecontent.models import SiteContactSettings

from .models import InquiryNotification


class EmailDeliveryError(Exception):
    pass


def notify_new_inquiry(inquiry):
    contact_settings = SiteContactSettings.objects.filter(pk=1).first()
    recipient = contact_settings.inquiry_notification_email.strip() if contact_settings else ""
    if not recipient:
        return None

    notification, created = InquiryNotification.objects.get_or_create(
        inquiry=inquiry,
        defaults={"recipient": recipient},
    )
    if not created:
        return notification

    admin_path = reverse("lala_inquiry_detail", args=[inquiry.pk])
    admin_url = f"{settings.WAGTAILADMIN_BASE_URL.rstrip('/')}{admin_path}"
    property_name = inquiry.listing_title_snapshot or "General property inquiry"
    message = (
        "A new customer inquiry was submitted.\n\n"
        f"Customer: {inquiry.name}\n"
        f"Property: {property_name}\n"
        f"Interest: {inquiry.get_interest_display()}\n\n"
        f"Open the inquiry in the CMS: {admin_url}\n"
    )

    try:
        delivered = send_mail(
            subject=f"New Lala Land inquiry: {property_name}",
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False,
        )
        if delivered != 1:
            raise EmailDeliveryError("The email backend did not confirm delivery.")
    except Exception as error:  # Email alerts must never block the customer submission.
        notification.status = InquiryNotification.Status.FAILED
        notification.error_type = type(error).__name__
        notification.save(update_fields=["status", "error_type"])
        AuditEvent.objects.create(
            action="inquiry.notification_failed",
            target_type=inquiry._meta.label,
            target_id=str(inquiry.pk),
            metadata={
                "notification_id": str(notification.pk),
                "error_type": notification.error_type,
            },
        )
        return notification

    notification.status = InquiryNotification.Status.SENT
    notification.sent_at = timezone.now()
    notification.save(update_fields=["status", "sent_at"])
    AuditEvent.objects.create(
        action="inquiry.notification_sent",
        target_type=inquiry._meta.label,
        target_id=str(inquiry.pk),
        metadata={"notification_id": str(notification.pk)},
    )
    return notification
