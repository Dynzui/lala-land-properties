from django.urls import path, reverse
from wagtail import hooks
from wagtail.admin.menu import MenuItem

from apps.accounts.capabilities import Capability

from .admin_views import audit_log, revoke_invitation, staff_action, staff_dashboard


class OwnerMenuItem(MenuItem):
    def is_shown(self, request):
        return request.user.has_capability(Capability.STAFF_MANAGE)


@hooks.register("register_admin_urls")
def register_owner_admin_urls():
    return [
        path("staff-management/", staff_dashboard, name="lala_staff_dashboard"),
        path(
            "staff-management/<uuid:user_id>/<str:action>/", staff_action, name="lala_staff_action"
        ),
        path(
            "staff-management/invitations/<uuid:invitation_id>/revoke/",
            revoke_invitation,
            name="lala_revoke_invitation",
        ),
        path("audit-log/", audit_log, name="lala_audit_log"),
    ]


@hooks.register("register_admin_menu_item")
def register_staff_menu():
    return OwnerMenuItem(
        "Staff management", reverse("lala_staff_dashboard"), icon_name="group", order=800
    )


@hooks.register("register_admin_menu_item")
def register_audit_menu():
    return OwnerMenuItem("Audit log", reverse("lala_audit_log"), icon_name="history", order=810)
