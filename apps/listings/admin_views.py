from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from wagtail.admin.auth import require_admin_access

from apps.accounts.capabilities import Capability

from .admin_forms import GuidedListingForm
from .models import Listing
from .services import archive_listing, publish_listing, restore_listing


def _require_listing_access(user):
    if not user.has_capability(Capability.LISTING_MANAGE):
        raise PermissionDenied


@require_admin_access
def listing_workflow(request):
    _require_listing_access(request.user)
    listings = Listing.objects.select_related("property", "variant").prefetch_related("offers")
    return render(request, "listings/admin/workflow.html", {"listings": listings})


@require_admin_access
def guided_listing_create(request):
    _require_listing_access(request.user)
    form = GuidedListingForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        listing = form.save(actor=request.user)
        messages.success(
            request,
            f"{listing.title} was saved as a draft with its property details and price.",
        )
        return redirect("lala_listing_workflow")
    return render(request, "listings/admin/guided_form.html", {"form": form})


@require_admin_access
def guided_listing_edit(request, listing_id):
    _require_listing_access(request.user)
    listing = get_object_or_404(
        Listing.objects.select_related(
            "property__location",
            "property__property_type",
            "property__development",
            "property__variant",
            "variant__development",
            "variant__property_type",
        ).prefetch_related("offers"),
        pk=listing_id,
    )
    form = GuidedListingForm(request.POST or None, listing=listing)
    if request.method == "POST" and form.is_valid():
        listing = form.save(actor=request.user)
        messages.success(request, f"{listing.title} was updated successfully.")
        return redirect("lala_listing_workflow")
    return render(
        request,
        "listings/admin/guided_form.html",
        {"form": form, "listing": listing},
    )


@require_POST
@require_admin_access
def listing_action(request, listing_id, action):
    _require_listing_access(request.user)
    listing = get_object_or_404(Listing, pk=listing_id)
    actions = {
        "publish": publish_listing,
        "archive": archive_listing,
        "restore": restore_listing,
    }
    operation = actions.get(action)
    if operation is None:
        raise PermissionDenied
    try:
        operation(actor=request.user, listing=listing)
    except (ValidationError, ValueError) as error:
        detail = "; ".join(
            message
            for messages_for_field in getattr(error, "message_dict", {}).values()
            for message in messages_for_field
        ) or str(error)
        messages.error(request, detail)
    else:
        completed_actions = {
            "publish": "published",
            "archive": "archived",
            "restore": "restored as a draft",
        }
        messages.success(
            request,
            f"{listing.title} was {completed_actions[action]} successfully.",
        )
    return redirect("lala_listing_workflow")
