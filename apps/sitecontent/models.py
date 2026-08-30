import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.http import Http404
from django.utils import timezone
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.fields import RichTextField
from wagtail.models import Page
from wagtail.search import index


class ArticleCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=90, unique=True)
    description = models.CharField(max_length=240, blank=True)
    active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    panels = [
        FieldPanel("name"),
        FieldPanel("slug"),
        FieldPanel("description"),
        FieldPanel("active"),
        FieldPanel("sort_order"),
    ]

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name_plural = "article categories"

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        self.name = self.name.strip()
        self.full_clean()
        return super().save(*args, **kwargs)


class ResourceIndexPage(Page):
    intro = RichTextField(
        blank=True,
        features=["bold", "italic", "link"],
        default="Practical guidance for making informed property decisions.",
    )

    content_panels = Page.content_panels + [FieldPanel("intro")]
    parent_page_types = ["home.HomePage"]
    subpage_types = ["sitecontent.ArticlePage"]
    max_count = 1

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        articles = (
            ArticlePage.objects.child_of(self).live().public().filter(archived_at__isnull=True)
        )
        category_slug = request.GET.get("category", "").strip()
        if category_slug:
            articles = articles.filter(category__slug=category_slug, category__active=True)
        context.update(
            {
                "articles": articles.select_related("category", "cover_image"),
                "categories": ArticleCategory.objects.filter(active=True),
                "selected_category": category_slug,
            }
        )
        return context


class AboutPage(Page):
    eyebrow = models.CharField(max_length=80, default="Meet Lala")
    headline = models.CharField(
        max_length=180,
        default="Real estate should feel more understandable.",
    )
    introduction = models.TextField(
        max_length=700,
        default=(
            "Lala Land Properties was created to make the journey toward homeownership "
            "feel less overwhelming and more understandable."
        ),
    )
    portrait = models.ForeignKey(
        "wagtailimages.Image",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="about_page_portraits",
    )
    portrait_alt_text = models.CharField(max_length=250, blank=True)
    story = RichTextField(
        features=["h2", "h3", "bold", "italic", "ol", "ul", "link", "blockquote"],
        default=(
            "<p>Hi, I’m Lala. I help buyers understand their options, discover properties "
            "that suit their needs, and move forward with confidence.</p>"
        ),
    )
    philosophy_quote = models.CharField(
        max_length=240,
        default="Guidance, not pressure.",
    )
    approach = RichTextField(
        features=["h2", "h3", "bold", "italic", "ol", "ul", "link", "blockquote"],
        default=(
            "<p>Every buyer has different needs, priorities, and goals. Clear information, "
            "realistic expectations, and personalized service come first.</p>"
        ),
    )
    community = RichTextField(
        features=["h2", "h3", "bold", "italic", "ol", "ul", "link"],
        default=(
            "<p>With local knowledge of Negros Occidental, Lala Land helps people explore "
            "communities and properties with context—not just sales listings.</p>"
        ),
    )
    affiliation = models.CharField(
        max_length=160,
        default="Proudly affiliated with PRES Realty",
    )

    content_panels = Page.content_panels + [
        MultiFieldPanel(
            [FieldPanel("eyebrow"), FieldPanel("headline"), FieldPanel("introduction")],
            heading="Page introduction",
        ),
        MultiFieldPanel(
            [FieldPanel("portrait"), FieldPanel("portrait_alt_text")],
            heading="Portrait",
        ),
        FieldPanel("story"),
        FieldPanel("philosophy_quote"),
        FieldPanel("approach"),
        FieldPanel("community"),
        FieldPanel("affiliation"),
    ]

    parent_page_types = ["home.HomePage"]
    subpage_types = []
    max_count = 1

    search_fields = Page.search_fields + [
        index.SearchField("headline"),
        index.SearchField("introduction"),
        index.SearchField("story"),
        index.SearchField("approach"),
        index.SearchField("community"),
    ]

    def clean(self):
        super().clean()
        if self.portrait_id and not self.portrait_alt_text.strip():
            raise ValidationError(
                {"portrait_alt_text": "Describe the portrait for screen-reader users."}
            )


class ArticlePage(Page):
    summary = models.CharField(max_length=300)
    category = models.ForeignKey(
        ArticleCategory,
        on_delete=models.PROTECT,
        related_name="articles",
    )
    cover_image = models.ForeignKey(
        "wagtailimages.Image",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="article_covers",
    )
    cover_alt_text = models.CharField(max_length=250, blank=True)
    body = RichTextField(
        features=[
            "h2",
            "h3",
            "bold",
            "italic",
            "ol",
            "ul",
            "hr",
            "link",
            "document-link",
            "image",
            "blockquote",
        ]
    )
    author_name = models.CharField(max_length=120, default="Lala Land Properties")
    featured = models.BooleanField(default=False)
    archived = models.BooleanField(
        default=False,
        help_text="Hide this article from the public site while keeping its CMS record.",
    )
    archived_at = models.DateTimeField(blank=True, null=True)

    content_panels = Page.content_panels + [
        FieldPanel("summary"),
        FieldPanel("category"),
        FieldPanel("cover_image"),
        FieldPanel("cover_alt_text"),
        FieldPanel("body"),
        MultiFieldPanel(
            [FieldPanel("author_name"), FieldPanel("featured"), FieldPanel("archived")],
            heading="Article settings",
        ),
        FieldPanel("archived_at", read_only=True),
    ]

    parent_page_types = ["sitecontent.ResourceIndexPage"]
    subpage_types = []

    search_fields = Page.search_fields + [
        index.SearchField("summary"),
        index.SearchField("body"),
        index.FilterField("featured"),
        index.FilterField("archived_at"),
    ]

    class Meta:
        ordering = ["-first_published_at", "-latest_revision_created_at"]

    def clean(self):
        super().clean()
        if not self.summary.strip():
            raise ValidationError({"summary": "A public article summary is required."})
        if not str(self.body).strip():
            raise ValidationError({"body": "Article content is required."})
        if self.cover_image_id and not self.cover_alt_text.strip():
            raise ValidationError(
                {"cover_alt_text": "Describe the cover image for screen-reader users."}
            )

    def serve(self, request, *args, **kwargs):
        if self.archived:
            raise Http404
        return super().serve(request, *args, **kwargs)

    def save(self, *args, **kwargs):
        if self.archived and self.archived_at is None:
            self.archived_at = timezone.now()
        elif not self.archived:
            self.archived_at = None
        return super().save(*args, **kwargs)

    @property
    def publication_date(self):
        return self.first_published_at or self.latest_revision_created_at or timezone.now()

    def archive(self, *, user=None):
        if not self.archived:
            self.archived = True
            self.archived_at = timezone.now()
            self.save_revision(user=user)
            if self.live:
                self.unpublish(user=user)
