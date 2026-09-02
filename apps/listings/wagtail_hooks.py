from wagtail import hooks
from wagtail.snippets.models import register_snippet
from django.urls import path, reverse
from wagtail.admin.menu import MenuItem
from wagtail.snippets.views.snippets import CreateView, SnippetViewSet

from .admin_views import listing_action, listing_workflow
from .models import Listing, Offer
from .services import record_listing_change, serialize_record


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
        path("listing-workflow/<uuid:listing_id>/<str:action>/", listing_action, name="lala_listing_action"),
    ]


@hooks.register("register_admin_menu_item")
def register_listing_workflow_menu_item():
    return MenuItem("Listing workflow", reverse("lala_listing_workflow"), icon_name="doc-full", order=210)


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
