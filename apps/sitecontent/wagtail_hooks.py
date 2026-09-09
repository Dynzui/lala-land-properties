from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.shortcuts import redirect
from django.urls import path, reverse
from wagtail import hooks
from wagtail.admin.menu import MenuItem
from wagtail.permission_policies.base import ModelPermissionPolicy
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet

from apps.accounts.capabilities import Capability
from apps.audittrail.models import AuditEvent
from home.models import HomePage

from .admin_views import content_dashboard
from .models import AboutPage, ArticleCategory, ArticlePage, ResourceIndexPage, SiteContactSettings


def request_actor(request):
    return getattr(request, "user", None)


class ArticleCategoryViewSet(SnippetViewSet):
    model = ArticleCategory
    icon = "tag"
    list_display = ["name", "active", "sort_order", "updated_at"]
    list_filter = ["active"]
    search_fields = ["name", "description"]
    ordering = ["sort_order", "name"]


class GlobalContentPermissionPolicy(ModelPermissionPolicy):
    """Keep global website copy owner-only, even when a URL is opened directly."""

    def user_has_permission(self, user, action):  # noqa: ARG002
        return user.is_active and (
            user.is_superuser or user.has_capability(Capability.GLOBAL_CONTENT_MANAGE)
        )

    def users_with_any_permission(self, actions):  # noqa: ARG002
        user_model = get_user_model()
        return user_model.objects.filter(
            Q(is_superuser=True) | Q(role=user_model.Role.OWNER),
            is_active=True,
        ).distinct()


class SiteContactSettingsViewSet(SnippetViewSet):
    model = SiteContactSettings
    icon = "mail"
    menu_label = "Contact page settings"

    @property
    def permission_policy(self):
        return GlobalContentPermissionPolicy(self.model)


register_snippet(ArticleCategory, viewset=ArticleCategoryViewSet)
register_snippet(SiteContactSettings, viewset=SiteContactSettingsViewSet)


class ContentMenuItem(MenuItem):
    def is_shown(self, request):
        return request.user.has_capability(Capability.ARTICLE_MANAGE)


@hooks.register("register_admin_urls")
def register_content_admin_urls():
    return [
        path("website-content/", content_dashboard, name="lala_content_dashboard"),
    ]


@hooks.register("register_admin_menu_item")
def register_content_menu_item():
    return ContentMenuItem(
        "Website content",
        reverse("lala_content_dashboard"),
        icon_name="doc-full",
        order=200,
    )


@hooks.register("construct_main_menu")
def replace_page_explorer_with_content_dashboard(request, menu_items):
    if request.user.has_capability(Capability.ARTICLE_MANAGE):
        menu_items[:] = [
            item
            for item in menu_items
            if item.name not in {"explorer", "pages"} and item.label != "Pages"
        ]


def _protect_essential_page(request, page, action):
    if isinstance(page.specific, (HomePage, AboutPage, ResourceIndexPage)):
        messages.error(
            request,
            f"{page.title} is an essential website page and cannot be {action}.",
        )
        return redirect("lala_content_dashboard")
    return None


@hooks.register("before_delete_page")
def prevent_essential_page_deletion(request, page):
    return _protect_essential_page(request, page, "deleted")


@hooks.register("before_move_page")
def prevent_essential_page_move(request, page, destination):  # noqa: ARG001
    return _protect_essential_page(request, page, "moved")


@hooks.register("before_unpublish_page")
def prevent_essential_page_unpublish(request, page):
    return _protect_essential_page(request, page, "unpublished")


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
    elif isinstance(instance, SiteContactSettings):
        AuditEvent.objects.create(
            actor=request_actor(request),
            action="site.contact_settings.created",
            target_type=instance._meta.label,
            target_id=str(instance.pk),
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
    elif isinstance(instance, SiteContactSettings):
        AuditEvent.objects.create(
            actor=request_actor(request),
            action="site.contact_settings.updated",
            target_type=instance._meta.label,
            target_id=str(instance.pk),
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
