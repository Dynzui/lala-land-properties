from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from wagtail.admin.auth import require_admin_access

from apps.accounts.capabilities import Capability
from apps.audittrail.models import AuditEvent

from .forms import StaffInvitationForm, StaffRoleForm, StaffStatusForm
from .models import StaffInvitation, User
from .services import create_staff_invitation, change_account_status, change_staff_role, revoke_staff_invitation


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
            messages.success(request, "Invitation created. Copy the one-time link now; the raw token is not stored.")
    staff = User.objects.filter(role__in=[User.Role.ADMIN, User.Role.MAINTAINER]).order_by("email")
    invitations = StaffInvitation.objects.select_related("invited_by").order_by("-created_at")[:30]
    return render(request, "accounts/admin/staff.html", {
        "staff": staff, "invitations": invitations, "invitation_form": invitation_form,
        "invitation_link": invitation_link, "role_choices": StaffRoleForm.base_fields["role"].choices,
        "status_choices": StaffStatusForm.base_fields["status"].choices,
    })


@require_POST
@require_admin_access
def staff_action(request, user_id, action):
    _require_owner(request.user)
    target = get_object_or_404(User, pk=user_id, role__in=[User.Role.ADMIN, User.Role.MAINTAINER])
    try:
        if action == "role":
            form = StaffRoleForm(request.POST)
            if form.is_valid(): change_staff_role(actor=request.user, target=target, role=form.cleaned_data["role"])
        elif action == "status":
            form = StaffStatusForm(request.POST)
            if form.is_valid(): change_account_status(actor=request.user, target=target, status=form.cleaned_data["status"])
        else:
            raise PermissionDenied
    except ValueError as error:
        messages.error(request, str(error))
    else:
        messages.success(request, f"Access updated for {target.email}. Active sessions were invalidated.")
    return redirect("lala_staff_dashboard")


@require_POST
@require_admin_access
def revoke_invitation(request, invitation_id):
    _require_owner(request.user)
    invitation = get_object_or_404(StaffInvitation, pk=invitation_id)
    try: revoke_staff_invitation(actor=request.user, invitation=invitation)
    except ValueError as error: messages.error(request, str(error))
    else: messages.success(request, "Invitation revoked.")
    return redirect("lala_staff_dashboard")


@require_admin_access
def audit_log(request):
    _require_owner(request.user)
    events = AuditEvent.objects.select_related("actor")[:250]
    return render(request, "accounts/admin/audit_log.html", {"events": events})
