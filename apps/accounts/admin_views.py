import re

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
from wagtail.admin.auth import require_admin_access

from apps.accounts.capabilities import Capability
from apps.audittrail.models import AuditEvent

from .forms import StaffInvitationForm, StaffRoleForm, StaffStatusForm
from .models import StaffInvitation, User
from .services import (
    change_account_status,
    change_staff_role,
    create_staff_invitation,
    revoke_staff_invitation,
)

AUDIT_ACTION_COPY = {
    "catalogue.location.deleted": ("Location deleted", "An unused catalogue location was removed."),
    "catalogue.property.created": ("Property created", "A property record was created."),
    "catalogue.record.created": ("Catalogue record created", "A catalogue record was created."),
    "catalogue.record.updated": ("Catalogue record updated", "A catalogue record was changed."),
    "inquiry.note.created": ("Inquiry note added", "A follow-up note was added to an inquiry."),
    "inquiry.notification_failed": (
        "Inquiry email failed",
        "The inquiry was saved, but its email alert failed.",
    ),
    "inquiry.notification_sent": (
        "Inquiry email sent",
        "The new-inquiry alert was accepted by the email service.",
    ),
    "inquiry.phone.viewed": (
        "Customer phone viewed",
        "Approved staff viewed a customer's phone number.",
    ),
    "inquiry.submitted": ("New inquiry received", "A customer submitted the contact form."),
    "inquiry.updated": ("Inquiry updated", "The inquiry's status or assignment was changed."),
    "listing.archived": ("Listing archived", "A public listing was archived."),
    "listing.published": ("Listing published", "A listing was published for customers."),
    "listing.record.created": ("Listing record created", "A listing record was created."),
    "listing.restored": (
        "Listing restored as draft",
        "An archived listing was restored for review.",
    ),
    "site.contact_settings.updated": (
        "Contact settings updated",
        "The contact page settings were changed.",
    ),
    "staff.invitation.created": (
        "Staff invitation created",
        "A private staff invitation was created.",
    ),
    "staff.invitation.revoked": (
        "Staff invitation revoked",
        "A pending staff invitation was revoked.",
    ),
    "staff.role.changed": ("Staff role changed", "A staff member's access role was changed."),
    "staff.status.changed": ("Staff status changed", "A staff account's status was changed."),
}

AUDIT_RECORD_LABELS = {
    "inquiries.Inquiry": "Inquiry",
    "listings.Listing": "Listing",
    "listings.Offer": "Price and availability",
    "properties.Development": "Development",
    "properties.Location": "Location",
    "properties.Property": "Property",
    "properties.Variant": "House model",
    "sitecontent.SiteContactSettings": "Contact settings",
}


def _audit_record_label(target_type):
    if target_type in AUDIT_RECORD_LABELS:
        return AUDIT_RECORD_LABELS[target_type]

    model_name = target_type.rsplit(".", 1)[-1].replace("_", " ")
    model_name = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", model_name)
    model_name = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", model_name)
    words = [word if word.isupper() else word.lower() for word in model_name.split()]
    if words and not words[0].isupper():
        words[0] = words[0].capitalize()
    return " ".join(words)


def _audit_entries(events):
    events = list(events)
    submitted_ids = {event.target_id for event in events if event.action == "inquiry.submitted"}
    delivery_by_inquiry = {
        event.target_id: event
        for event in events
        if event.action in {"inquiry.notification_sent", "inquiry.notification_failed"}
    }
    entries = []
    for event in events:
        if event.action.startswith("inquiry.notification_") and event.target_id in submitted_ids:
            continue

        title, description = AUDIT_ACTION_COPY.get(
            event.action,
            (event.action.replace(".", " ").replace("_", " ").title(), "Recorded system activity."),
        )
        delivery = (
            delivery_by_inquiry.get(event.target_id)
            if event.action == "inquiry.submitted"
            else None
        )
        status = ""
        status_tone = ""
        if delivery:
            if delivery.action == "inquiry.notification_sent":
                status = "Email notification sent"
                status_tone = "success"
                description = "A customer inquiry was saved and the staff email alert was sent."
            else:
                status = "Email notification failed"
                status_tone = "critical"
                description = "The customer inquiry was saved, but the staff email alert failed."

        record_url = ""
        if event.target_type == "inquiries.Inquiry" and event.target_id:
            record_url = reverse("lala_inquiry_detail", args=[event.target_id])

        entries.append(
            {
                "event": event,
                "title": title,
                "description": description,
                "status": status,
                "status_tone": status_tone,
                "record_label": _audit_record_label(event.target_type),
                "record_url": record_url,
            }
        )
    return entries


def _require_owner(user):
    if not user.has_capability(Capability.STAFF_MANAGE):
        raise PermissionDenied


@require_admin_access
def staff_dashboard(request):
    _require_owner(request.user)
    invitation_form = StaffInvitationForm(request.POST or None)
    invitation_link = None
    if request.method == "POST" and invitation_form.is_valid():
        try:
            created = create_staff_invitation(actor=request.user, **invitation_form.cleaned_data)
        except ValueError as error:
            invitation_form.add_error(None, str(error))
        else:
            from django.urls import reverse

            invitation_link = request.build_absolute_uri(
                reverse("accounts:accept_invitation", args=[created.token])
            )
            messages.success(
                request,
                "Invitation created. Copy the one-time link now; the raw token is not stored.",
            )
    staff = User.objects.filter(role__in=[User.Role.ADMIN, User.Role.MAINTAINER]).order_by("email")
    invitations = StaffInvitation.objects.select_related("invited_by").order_by("-created_at")[:30]
    return render(
        request,
        "accounts/admin/staff.html",
        {
            "staff": staff,
            "invitations": invitations,
            "invitation_form": invitation_form,
            "invitation_link": invitation_link,
            "role_choices": StaffRoleForm.base_fields["role"].choices,
            "status_choices": StaffStatusForm.base_fields["status"].choices,
        },
    )


@require_POST
@require_admin_access
def staff_action(request, user_id, action):
    _require_owner(request.user)
    target = get_object_or_404(User, pk=user_id, role__in=[User.Role.ADMIN, User.Role.MAINTAINER])
    try:
        if action == "role":
            form = StaffRoleForm(request.POST)
            if form.is_valid():
                change_staff_role(actor=request.user, target=target, role=form.cleaned_data["role"])
        elif action == "status":
            form = StaffStatusForm(request.POST)
            if form.is_valid():
                change_account_status(
                    actor=request.user, target=target, status=form.cleaned_data["status"]
                )
        else:
            raise PermissionDenied
    except ValueError as error:
        messages.error(request, str(error))
    else:
        messages.success(
            request, f"Access updated for {target.email}. Active sessions were invalidated."
        )
    return redirect("lala_staff_dashboard")


@require_POST
@require_admin_access
def revoke_invitation(request, invitation_id):
    _require_owner(request.user)
    invitation = get_object_or_404(StaffInvitation, pk=invitation_id)
    try:
        revoke_staff_invitation(actor=request.user, invitation=invitation)
    except ValueError as error:
        messages.error(request, str(error))
    else:
        messages.success(request, "Invitation revoked.")
    return redirect("lala_staff_dashboard")


@require_admin_access
def audit_log(request):
    _require_owner(request.user)
    events = AuditEvent.objects.select_related("actor")[:250]
    entries = _audit_entries(events)
    return render(request, "accounts/admin/audit_log.html", {"entries": entries})
