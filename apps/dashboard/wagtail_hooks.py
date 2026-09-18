from django.urls import reverse
from wagtail import hooks
from wagtail.admin.menu import MenuItem

from apps.accounts.capabilities import Capability


class DashboardMenuItem(MenuItem):
    def is_shown(self, request):
        return any(
            request.user.has_capability(capability)
            for capability in (
                Capability.INQUIRY_MANAGE,
                Capability.LISTING_MANAGE,
                Capability.ARTICLE_MANAGE,
            )
        )


@hooks.register("register_admin_menu_item")
def register_dashboard_menu_item():
    return DashboardMenuItem(
        "Dashboard",
        reverse("lala_cms_dashboard"),
        icon_name="home",
        order=100,
    )
