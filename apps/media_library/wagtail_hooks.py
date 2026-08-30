from wagtail import hooks
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet

from .models import CatalogueMedia
from .services import media_snapshot, record_media_change


class CatalogueMediaViewSet(SnippetViewSet):
    model = CatalogueMedia
    icon = "image"
    list_display = ["image", "target", "is_cover", "sort_order", "updated_at"]
    list_filter = ["is_cover", "property", "variant", "development"]
    search_fields = ["image__title", "alt_text", "caption"]
    ordering = ["property", "variant", "development", "sort_order"]


register_snippet(CatalogueMedia, viewset=CatalogueMediaViewSet)


@hooks.register("before_edit_snippet")
def capture_media_before_edit(request, instance):
    if isinstance(instance, CatalogueMedia):
        request._lala_media_before = media_snapshot(instance)


@hooks.register("after_create_snippet")
def audit_media_create(request, instance):
    if isinstance(instance, CatalogueMedia):
        record_media_change(actor=request.user, media=instance, action="catalogue.media.created")


@hooks.register("after_edit_snippet")
def audit_media_edit(request, instance):
    if isinstance(instance, CatalogueMedia):
        record_media_change(
            actor=request.user,
            media=instance,
            action="catalogue.media.updated",
            before=getattr(request, "_lala_media_before", None),
        )
