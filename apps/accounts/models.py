import uuid

from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as DjangoUserManager
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone


class UserManager(DjangoUserManager):
    def _create_user(self, username, email, password, **extra_fields):
        email = self.normalize_email(email).strip().lower()
        return super()._create_user(username, email, password, **extra_fields)


class User(AbstractUser):
    """Staff/customer identity; detailed capabilities are enforced separately."""

    class Role(models.TextChoices):
        OWNER = "OWNER", "Owner"
        ADMIN = "ADMIN", "Admin"
        CUSTOMER = "CUSTOMER", "Customer"
        MAINTAINER = "MAINTAINER", "Maintainer"

    class Status(models.TextChoices):
        INVITED = "INVITED", "Invited"
        ACTIVE = "ACTIVE", "Active"
        SUSPENDED = "SUSPENDED", "Suspended"
        DISABLED = "DISABLED", "Disabled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=16, choices=Role.choices)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.INVITED,
    )
    disabled_at = models.DateTimeField(blank=True, null=True)
    session_version = models.PositiveIntegerField(default=1)
    objects = UserManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(Lower("email"), name="accounts_user_email_ci_unique"),
        ]

    def __str__(self) -> str:
        return self.get_full_name() or self.email or self.username

    def save(self, *args, **kwargs):
        should_be_active = self.status == self.Status.ACTIVE
        if self.is_active != should_be_active:
            self.is_active = should_be_active
            update_fields = kwargs.get("update_fields")
            if update_fields is not None:
                kwargs["update_fields"] = {*update_fields, "is_active"}
        return super().save(*args, **kwargs)

    def has_capability(self, capability: str) -> bool:
        from .capabilities import user_has_capability

        return user_has_capability(self, capability)


class StaffInvitation(models.Model):
    """Single-use, expiring invitation; the raw token is never stored."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField()
    role = models.CharField(
        max_length=16,
        choices=(
            (User.Role.ADMIN, "Admin"),
            (User.Role.MAINTAINER, "Maintainer"),
        ),
    )
    token_digest = models.CharField(max_length=64, unique=True)
    invited_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="staff_invitations_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(blank=True, null=True)
    revoked_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        indexes = [models.Index(fields=["email", "expires_at"])]

    def __str__(self) -> str:
        return f"{self.email} ({self.get_role_display()})"

    @property
    def is_usable(self) -> bool:
        return (
            self.accepted_at is None
            and self.revoked_at is None
            and self.expires_at > timezone.now()
        )
