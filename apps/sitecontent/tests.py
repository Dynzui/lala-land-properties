import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from wagtail.models import GroupPagePermission

from home.models import HomePage

from .models import (
    AboutPage,
    ArticleCategory,
    ArticlePage,
    ResourceIndexPage,
    SiteContactSettings,
)

pytestmark = pytest.mark.django_db


def make_category(**overrides):
    values = {"name": "Homebuyer Guides", "slug": "homebuyer-guides"}
    values.update(overrides)
    return ArticleCategory.objects.create(**values)


def make_article(*, live=True, **overrides):
    resources = ResourceIndexPage.objects.first()
    category = overrides.pop("category", None) or make_category()
    values = {
        "title": "Before You Start House Hunting",
        "slug": "before-you-start-house-hunting",
        "summary": "A practical checklist before viewing properties.",
        "category": category,
        "body": "<p>Start with a clear budget and a list of priorities.</p>",
    }
    values.update(overrides)
    article = ArticlePage(**values)
    if not live:
        article.live = False
    resources.add_child(instance=article)
    revision = article.save_revision()
    if live:
        revision.publish()
        article.refresh_from_db()
    return article


def test_resources_page_is_created_and_public(client):
    resources = ResourceIndexPage.objects.get()

    response = client.get(resources.url)

    assert response.status_code == 200
    assert b"Learn before you" in response.content


def test_about_page_is_created_and_public(client):
    about = AboutPage.objects.get()

    response = client.get(about.url)

    assert response.status_code == 200
    assert b"Real estate should feel more understandable" in response.content
    assert b"Guidance, not pressure" in response.content


def test_about_portrait_requires_accessible_alt_text():
    about = AboutPage(
        title="About",
        portrait_id=1,
        portrait_alt_text="",
    )

    with pytest.raises(ValidationError, match="screen-reader"):
        about.clean()


def test_homepage_links_to_about_page(client):
    about = AboutPage.objects.get()

    response = client.get(HomePage.objects.get().url)

    assert response.status_code == 200
    assert about.url.encode() in response.content


def test_resource_index_only_shows_live_non_archived_articles(client):
    visible = make_article()
    make_article(
        live=False,
        title="Draft Advice",
        slug="draft-advice",
        category=visible.category,
    )
    archived = make_article(
        title="Old Advice",
        slug="old-advice",
        category=visible.category,
    )
    archived.archived = True
    archived.save()

    response = client.get(ResourceIndexPage.objects.get().url)

    assert response.status_code == 200
    assert visible.title.encode() in response.content
    assert b"Draft Advice" not in response.content
    assert b"Old Advice" not in response.content


def test_category_filter_limits_articles(client):
    buyer_article = make_article()
    community = make_category(name="Community", slug="community")
    make_article(title="Living in Bacolod", slug="living-in-bacolod", category=community)

    response = client.get(
        ResourceIndexPage.objects.get().url,
        {"category": buyer_article.category.slug},
    )

    assert buyer_article.title.encode() in response.content
    assert b"Living in Bacolod" not in response.content


def test_archived_article_returns_not_found_and_keeps_record(client):
    article = make_article()

    article.archive()
    article.refresh_from_db()

    assert article.archived is True
    assert article.archived_at is not None
    assert ArticlePage.objects.filter(pk=article.pk).exists()
    assert client.get(article.url).status_code == 404


def test_unarchiving_clears_archive_timestamp():
    article = make_article()
    article.archived = True
    article.save()
    assert article.archived_at is not None

    article.archived = False
    article.save()

    assert article.archived_at is None


def test_cover_image_requires_accessible_alt_text():
    article = ArticlePage(
        title="Accessible Article",
        slug="accessible-article",
        summary="Summary",
        category=make_category(),
        body="<p>Body</p>",
        cover_image_id=1,
        cover_alt_text="",
    )

    with pytest.raises(ValidationError, match="screen-reader"):
        article.clean()


def test_homepage_context_only_features_public_active_articles(rf):
    article = make_article(featured=True)
    make_article(
        title="Ordinary Article",
        slug="ordinary-article",
        category=article.category,
        featured=False,
    )
    request = rf.get("/")

    context = HomePage.objects.get().get_context(request)

    assert list(context["featured_articles"]) == [article]


@pytest.mark.parametrize(
    ("role", "expected_group", "expected_root_model"),
    [
        ("OWNER", "Lala Land Owners", HomePage),
        ("ADMIN", "Lala Land Content Admins", ResourceIndexPage),
    ],
)
def test_staff_roles_receive_scoped_wagtail_page_permissions(
    role,
    expected_group,
    expected_root_model,
):
    user_model = get_user_model()
    user = user_model.objects.create_user(
        username=f"{role.lower()}-editor",
        email=f"{role.lower()}-editor@example.test",
        password="safe-test-password",
        role=role,
        status=user_model.Status.ACTIVE,
    )

    assert user.groups.filter(name=expected_group).exists()
    page_permissions = GroupPagePermission.objects.filter(group__name=expected_group)
    assert set(page_permissions.values_list("permission__codename", flat=True)) == {
        "add_page",
        "change_page",
        "lock_page",
        "publish_page",
        "unlock_page",
    }
    assert page_permissions.filter(page_id=expected_root_model.objects.get().pk).exists()


def test_admin_has_scoped_about_page_permissions():
    about = AboutPage.objects.get()

    page_permissions = GroupPagePermission.objects.filter(
        group__name="Lala Land Content Admins",
        page_id=about.pk,
    )

    assert set(page_permissions.values_list("permission__codename", flat=True)) == {
        "add_page",
        "change_page",
        "lock_page",
        "publish_page",
        "unlock_page",
    }


def test_customer_receives_no_editor_group():
    user_model = get_user_model()
    customer = user_model.objects.create_user(
        username="article-customer",
        email="article-customer@example.test",
        password="safe-test-password",
        role=user_model.Role.CUSTOMER,
        status=user_model.Status.ACTIVE,
    )

    assert not customer.groups.filter(name__startswith="Lala Land").exists()


def test_social_contact_settings_are_singleton_and_render_when_configured(client):
    settings = SiteContactSettings.objects.get(pk=1)
    settings.facebook_url = "https://facebook.com/lalaland.example"
    settings.instagram_url = "https://instagram.com/lalaland.example"
    settings.save()

    duplicate = SiteContactSettings(facebook_url="https://example.com/other")
    with pytest.raises(ValidationError, match="already exist"):
        duplicate.save()

    assert SiteContactSettings.objects.count() == 1
    response = client.get("/contact/")
    assert response.status_code == 200
    assert b"https://facebook.com/lalaland.example" in response.content
    assert b"https://instagram.com/lalaland.example" in response.content


def test_article_publication_date_falls_back_to_revision_timestamp():
    article = make_article(live=False)

    assert article.publication_date <= timezone.now()
