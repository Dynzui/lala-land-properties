from django.contrib import messages
from django.shortcuts import redirect
from wagtail import hooks
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet

from apps.audittrail.models import AuditEvent

from .forms import LocationAdminForm
from .models import Development, Location, Property, PropertyType, Variant
from .services import record_catalog_change, serialize_catalog_record

CATALOG_MODELS = (PropertyType, Location, Development, Variant, Property)


class MobileCatalogueIndexMixin:
    index_template_name = "properties/admin/catalogue_index.html"
    create_template_name = "properties/admin/catalogue_create.html"
    edit_template_name = "properties/admin/catalogue_edit.html"


class PropertyTypeViewSet(MobileCatalogueIndexMixin, SnippetViewSet):
    model = PropertyType
    icon = "tag"
    list_display = ["name", "active", "sort_order", "updated_at"]
    list_filter = ["active"]
    search_fields = ["name", "description"]
    ordering = ["sort_order", "name"]


class LocationViewSet(MobileCatalogueIndexMixin, SnippetViewSet):
    model = Location
    icon = "site"
    list_display = ["public_label", "visibility", "city_municipality", "province"]
    list_filter = ["visibility", "province", "city_municipality"]
    search_fields = ["public_label", "city_municipality", "province", "barangay"]
    ordering = ["province", "city_municipality", "public_label"]

    def get_form_class(self, for_update=False):
        return LocationAdminForm


class DevelopmentViewSet(MobileCatalogueIndexMixin, SnippetViewSet):
    model = Development
    icon = "home"
    list_display = ["name", "development_type", "status", "updated_at"]
    list_filter = ["development_type", "status"]
    search_fields = ["name", "summary", "developer_name"]
    ordering = ["name"]

class VariantViewSet(MobileCatalogueIndexMixin, SnippetViewSet):
    model = Variant
    icon = "list-ul"
    list_display = ["name", "development", "property_type", "status", "updated_at"]
    list_filter = ["status", "property_type", "development"]
    search_fields = ["name", "description", "development__name"]
    ordering = ["development__name", "name"]


class PropertyViewSet(MobileCatalogueIndexMixin, SnippetViewSet):
    model = Property
    icon = "key"
    list_display = [
        "reference_code",
        "title_override",
        "property_type",
        "inventory_status",
        "updated_at",
    ]
    list_filter = ["inventory_status", "property_type", "development"]
    search_fields = ["reference_code", "title_override", "development__name"]
    ordering = ["reference_code"]


register_snippet(PropertyType, viewset=PropertyTypeViewSet)
register_snippet(Location, viewset=LocationViewSet)
register_snippet(Development, viewset=DevelopmentViewSet)
register_snippet(Variant, viewset=VariantViewSet)
register_snippet(Property, viewset=PropertyViewSet)


@hooks.register("before_edit_snippet")
def capture_catalogue_before_edit(request, instance):
    if isinstance(instance, Development) and request.method == "POST":
        requested_status = request.POST.get("status")
        if (
            instance.status != Development.Status.ARCHIVED
            and requested_status == Development.Status.ARCHIVED
        ):
            blocker = instance.archive_blocker_message()
            if blocker:
                messages.error(request, blocker)
                return redirect(request.path)
        if (
            instance.status == Development.Status.ARCHIVED
            and requested_status != Development.Status.ARCHIVED
        ):
            mutable_post = request.POST.copy()
            mutable_post["status"] = Development.Status.DRAFT
            request.POST = mutable_post
            instance.archived_at = None
    if isinstance(instance, CATALOG_MODELS):
        request._lala_catalogue_before = serialize_catalog_record(instance)


@hooks.register("after_create_snippet")
def audit_catalogue_create(request, instance):
    if isinstance(instance, CATALOG_MODELS):
        record_catalog_change(
            actor=request.user,
            record=instance,
            action="catalogue.record.created",
            change_summary="Created through Wagtail",
        )


@hooks.register("after_edit_snippet")
def audit_catalogue_edit(request, instance):
    if isinstance(instance, CATALOG_MODELS):
        before = getattr(request, "_lala_catalogue_before", None)
        action = "catalogue.record.updated"
        summary = "Updated through Wagtail"
        if isinstance(instance, Development) and before:
            previous_status = before.get("status")
            if (
                previous_status != Development.Status.ARCHIVED
                and instance.status == Development.Status.ARCHIVED
            ):
                action = "catalogue.development.archived"
                summary = "Archived through Wagtail; dependent records were left unchanged"
            elif (
                previous_status == Development.Status.ARCHIVED
                and instance.status != Development.Status.ARCHIVED
            ):
                action = "catalogue.development.restored"
                summary = "Restored through Wagtail; dependent listings remain unpublished"
        record_catalog_change(
            actor=request.user,
            record=instance,
            action=action,
            before=before,
            change_summary=summary,
        )


@hooks.register("before_delete_snippet")
def capture_location_deletions(request, instances):
    """Keep non-sensitive identifiers because Django clears PKs after deletion."""
    request._lala_location_deletions = [
        {
            "target_id": str(instance.pk),
            "public_label": instance.public_label,
            "region": instance.region,
            "province": instance.province,
            "city_municipality": instance.city_municipality,
        }
        for instance in instances
        if isinstance(instance, Location)
    ]


@hooks.register("after_delete_snippet")
def audit_location_deletions(request, instances):
    for deleted in getattr(request, "_lala_location_deletions", []):
        AuditEvent.objects.create(
            actor=request.user,
            action="catalogue.location.deleted",
            target_type=Location._meta.label,
            target_id=deleted.pop("target_id"),
            metadata=deleted,
        )
