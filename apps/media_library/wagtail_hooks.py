from wagtail import hooks
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet
from wagtail.snippets.views.snippets import CreateView

from .models import CatalogueMedia


class CatalogueMediaCreateView(CreateView):
    def get_initial(self):
        initial = super().get_initial()
        for target in ("property", "variant", "development"):
            if self.request.GET.get(target):
                initial[target] = self.request.GET[target]
        return initial
from .services import media_snapshot, record_media_change


class CatalogueMediaViewSet(SnippetViewSet):
    model = CatalogueMedia
    add_view_class = CatalogueMediaCreateView
    icon = "image"
    list_display = ["image", "kind", "target", "is_cover", "sort_order", "updated_at"]
    list_filter = ["kind", "is_cover", "property", "variant", "development"]
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
