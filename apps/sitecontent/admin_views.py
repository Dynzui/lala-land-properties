from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from django.urls import reverse
from wagtail.admin.auth import require_admin_access

from apps.accounts.capabilities import Capability
from home.models import HomePage

from .models import AboutPage, ArticlePage, ResourceIndexPage, SiteContactSettings


def _page_status(page):
    if page.live and page.has_unpublished_changes:
        return "Published — changes waiting"
    if page.live:
        return "Published"
    return "Draft"


def _edit_page_url(page):
    return reverse("wagtailadmin_pages:edit", args=[page.pk]) if page else None


@require_admin_access
def content_dashboard(request):
    if not request.user.has_capability(Capability.ARTICLE_MANAGE):
        raise PermissionDenied

    home = HomePage.objects.first()
    about = AboutPage.objects.first()
    resources = ResourceIndexPage.objects.first()
    contact = SiteContactSettings.objects.filter(pk=1).first()
    can_manage_global_content = request.user.has_capability(Capability.GLOBAL_CONTENT_MANAGE)

    content_cards = [
        {
            "name": "Home page",
            "description": "Hero text, introductions, resource headings, and calls to action.",
            "status": _page_status(home) if home else "Not created",
            "url": _edit_page_url(home) if can_manage_global_content else None,
            "action": "Edit home page",
            "owner_only": not can_manage_global_content,
        },
        {
            "name": "About Lala",
            "description": "Lala's introduction, story, portrait, and approach.",
            "status": _page_status(about) if about else "Not created",
            "url": _edit_page_url(about),
            "action": "Edit About page",
        },
        {
            "name": "Resources",
            "description": "The introduction shown above the article library.",
            "status": _page_status(resources) if resources else "Not created",
            "url": _edit_page_url(resources),
            "action": "Edit Resources page",
        },
        {
            "name": "Contact page",
            "description": "Page text, response expectations, contact details, and social links.",
            "status": "Configured" if contact else "Not configured",
            "url": (
                reverse(
                    "wagtailsnippets_sitecontent_sitecontactsettings:edit",
                    args=[contact.pk],
                )
                if contact and can_manage_global_content
                else None
            ),
            "action": "Edit contact page",
            "owner_only": not can_manage_global_content,
        },
    ]

    articles = ArticlePage.objects.select_related("category").order_by(
        "-latest_revision_created_at", "title"
    )
    article_rows = []
    for article in articles:
        if article.archived:
            status = "Archived"
        else:
            status = _page_status(article)
        article_rows.append(
            {
                "title": article.title,
                "category": article.category.name,
                "status": status,
                "updated_at": article.latest_revision_created_at,
                "edit_url": _edit_page_url(article),
            }
        )

    add_article_url = None
    if resources:
        add_article_url = reverse(
            "wagtailadmin_pages:add",
            args=[
                ArticlePage._meta.app_label,
                ArticlePage._meta.model_name,
                resources.pk,
            ],
        )

    return render(
        request,
        "sitecontent/admin/content_dashboard.html",
        {
            "content_cards": content_cards,
            "articles": article_rows,
            "add_article_url": add_article_url,
            "manage_categories_url": reverse("wagtailsnippets_sitecontent_articlecategory:list"),
            "advanced_pages_url": (
                reverse("wagtailadmin_explore_root") if can_manage_global_content else None
            ),
        },
    )
