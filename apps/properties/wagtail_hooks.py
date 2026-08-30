from wagtail import hooks
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet

from .models import Development, Location, Property, PropertyType, Variant
from .services import record_catalog_change, serialize_catalog_record

CATALOG_MODELS = (PropertyType, Location, Development, Variant, Property)


class PropertyTypeViewSet(SnippetViewSet):
    model = PropertyType
    icon = "tag"
    list_display = ["name", "active", "sort_order", "updated_at"]
    list_filter = ["active"]
    search_fields = ["name", "description"]
    ordering = ["sort_order", "name"]


class LocationViewSet(SnippetViewSet):
    model = Location
    icon = "site"
    list_display = ["public_label", "visibility", "city_municipality", "province"]
    list_filter = ["visibility", "province", "city_municipality"]
    search_fields = ["public_label", "city_municipality", "province", "barangay"]
    ordering = ["province", "city_municipality", "public_label"]


class DevelopmentViewSet(SnippetViewSet):
    model = Development
    icon = "home"
    list_display = ["name", "development_type", "status", "updated_at"]
    list_filter = ["development_type", "status"]
    search_fields = ["name", "summary", "developer_name"]
    ordering = ["name"]


class VariantViewSet(SnippetViewSet):
    model = Variant
    icon = "list-ul"
    list_display = ["name", "development", "property_type", "status", "updated_at"]
    list_filter = ["status", "property_type", "development"]
    search_fields = ["name", "description", "development__name"]
    ordering = ["development__name", "name"]


class PropertyViewSet(SnippetViewSet):
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
        record_catalog_change(
            actor=request.user,
            record=instance,
            action="catalogue.record.updated",
            before=getattr(request, "_lala_catalogue_before", None),
            change_summary="Updated through Wagtail",
        )
