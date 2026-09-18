from django.urls import path, reverse
from wagtail import hooks
from wagtail.admin.menu import MenuItem
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import CreateView, SnippetViewSet

from apps.accounts.capabilities import Capability

from .admin_views import (
    guided_listing_create,
    guided_listing_edit,
    listing_action,
    listing_workflow,
)
from .models import Listing, Offer
from .services import record_listing_change, serialize_record


class CapabilityMenuItem(MenuItem):
    def __init__(self, *args, capability, **kwargs):
        self.capability = capability
        super().__init__(*args, **kwargs)

    def is_shown(self, request):
        return request.user.has_capability(self.capability)


class ListingCreateView(CreateView):
    def save_instance(self):
        self.form.instance.workflow_status = Listing.WorkflowStatus.DRAFT
        self.form.instance.archived_at = None
        return super().save_instance()

    def get_success_url(self):
        return f"{reverse('wagtailsnippets_listings_offer:add')}?listing={self.object.pk}"


class ListingViewSet(SnippetViewSet):
    model = Listing
    add_view_class = ListingCreateView
    icon = "doc-full"
    list_display = [
        "title",
        "inventory_mode",
        "public_status",
        "workflow_status",
        "featured",
        "updated_at",
    ]
    list_filter = ["inventory_mode", "public_status", "workflow_status", "featured"]
    search_fields = ["title", "summary", "slug"]
    ordering = ["-published_at", "title"]


class OfferCreateView(CreateView):
    def get_initial(self):
        initial = super().get_initial()
        listing_id = self.request.GET.get("listing")
        if listing_id:
            initial["listing"] = listing_id
        return initial

    def get_success_url(self):
        return reverse("lala_listing_workflow")


class OfferViewSet(SnippetViewSet):
    model = Offer
    add_view_class = OfferCreateView
    icon = "pick"
    list_display = [
        "listing",
        "transaction_type",
        "price_display",
        "price_min",
        "active",
        "updated_at",
    ]
    list_filter = ["transaction_type", "price_display", "active"]
    search_fields = ["listing__title"]
    ordering = ["-active", "-updated_at"]


register_snippet(Listing, viewset=ListingViewSet)
register_snippet(Offer, viewset=OfferViewSet)


@hooks.register("register_admin_urls")
def register_listing_admin_urls():
    return [
        path("listing-workflow/", listing_workflow, name="lala_listing_workflow"),
        path("listing-workflow/add/", guided_listing_create, name="lala_guided_listing_add"),
        path(
            "listing-workflow/<uuid:listing_id>/edit/",
            guided_listing_edit,
            name="lala_guided_listing_edit",
        ),
        path(
            "listing-workflow/<uuid:listing_id>/<str:action>/",
            listing_action,
            name="lala_listing_action",
        ),
    ]


@hooks.register("register_admin_menu_item")
def register_listing_workflow_menu_item():
    return CapabilityMenuItem(
        "Listings",
        reverse("lala_listing_workflow"),
        icon_name="doc-full",
        order=210,
        capability=Capability.LISTING_MANAGE,
    )


@hooks.register("register_admin_menu_item")
def register_development_menu_item():
    return CapabilityMenuItem(
        "Developments",
        reverse("wagtailsnippets_properties_development:list"),
        icon_name="home",
        order=220,
        capability=Capability.PROPERTY_MANAGE,
    )


@hooks.register("register_admin_menu_item")
def register_site_settings_menu_item():
    return CapabilityMenuItem(
        "Site settings",
        reverse("wagtailsnippets_sitecontent_sitecontactsettings:list"),
        icon_name="cog",
        order=800,
        capability=Capability.GLOBAL_CONTENT_MANAGE,
    )


@hooks.register("construct_main_menu")
def hide_technical_snippet_menu(request, menu_items):
    """Keep normalized records accessible from guided links, not the main sidebar."""
    menu_items[:] = [item for item in menu_items if item.name != "snippets"]


@hooks.register("before_edit_snippet")
def capture_listing_before_edit(request, instance):
    if isinstance(instance, (Listing, Offer)):
        request._lala_listing_before = serialize_record(instance)


@hooks.register("after_create_snippet")
def audit_listing_create(request, instance):
    if isinstance(instance, (Listing, Offer)):
        record_listing_change(
            actor=request.user,
            record=instance,
            action="listing.record.created",
        )


@hooks.register("after_edit_snippet")
def audit_listing_edit(request, instance):
    if isinstance(instance, (Listing, Offer)):
        record_listing_change(
            actor=request.user,
            record=instance,
            action="listing.record.updated",
            before=getattr(request, "_lala_listing_before", None),
        )
