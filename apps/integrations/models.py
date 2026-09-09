import uuid

from django.db import models


class InquiryNotification(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SENT = "SENT", "Sent"
        FAILED = "FAILED", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    inquiry = models.OneToOneField(
        "inquiries.Inquiry",
        on_delete=models.PROTECT,
        related_name="email_notification",
    )
    recipient = models.EmailField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    error_type = models.CharField(max_length=120, blank=True)
    attempted_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-attempted_at"]

    def __str__(self):
        return f"New inquiry email for {self.inquiry_id}: {self.get_status_display()}"
