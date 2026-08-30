from wagtail import hooks
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet

from apps.audittrail.models import AuditEvent

from .models import AboutPage, ArticleCategory, ArticlePage


def request_actor(request):
    return getattr(request, "user", None)


class ArticleCategoryViewSet(SnippetViewSet):
    model = ArticleCategory
    icon = "tag"
    list_display = ["name", "active", "sort_order", "updated_at"]
    list_filter = ["active"]
    search_fields = ["name", "description"]
    ordering = ["sort_order", "name"]
    sort_order_field = "sort_order"


register_snippet(ArticleCategory, viewset=ArticleCategoryViewSet)


@hooks.register("after_create_snippet")
def audit_category_create(request, instance):
    if isinstance(instance, ArticleCategory):
        AuditEvent.objects.create(
            actor=request_actor(request),
            action="article.category.created",
            target_type=instance._meta.label,
            target_id=str(instance.pk),
            metadata={"name": instance.name},
        )


@hooks.register("after_edit_snippet")
def audit_category_edit(request, instance):
    if isinstance(instance, ArticleCategory):
        AuditEvent.objects.create(
            actor=request_actor(request),
            action="article.category.updated",
            target_type=instance._meta.label,
            target_id=str(instance.pk),
            metadata={"name": instance.name, "active": instance.active},
        )


@hooks.register("after_publish_page")
def audit_article_publish(request, page):
    specific_page = page.specific
    if isinstance(specific_page, (AboutPage, ArticlePage)):
        AuditEvent.objects.create(
            actor=request_actor(request),
            action=(
                "article.published" if isinstance(specific_page, ArticlePage) else "about.published"
            ),
            target_type=specific_page._meta.label,
            target_id=str(page.pk),
            metadata={"title": page.title},
        )


@hooks.register("after_unpublish_page")
def audit_article_unpublish(request, page):
    specific_page = page.specific
    if isinstance(specific_page, (AboutPage, ArticlePage)):
        AuditEvent.objects.create(
            actor=request_actor(request),
            action=(
                "article.unpublished"
                if isinstance(specific_page, ArticlePage)
                else "about.unpublished"
            ),
            target_type=specific_page._meta.label,
            target_id=str(page.pk),
            metadata={"title": page.title},
        )
