from django.db import models
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.models import Page


class HomePage(Page):
    hero_eyebrow = models.CharField(
        max_length=120,
        default="Real estate guidance for Negros Occidental",
    )
    hero_heading = models.TextField(max_length=160, default="Find a place\nto call")
    hero_emphasis = models.CharField(max_length=80, default="home.")
    hero_intro = models.TextField(
        max_length=400,
        default=(
            "Navigate your real estate journey with honest guidance, local knowledge, "
            "and service shaped around you."
        ),
    )
    hero_primary_cta = models.CharField(max_length=60, default="Explore properties")
    hero_secondary_cta = models.CharField(max_length=60, default="Let’s talk")

    intro_eyebrow = models.CharField(max_length=100, default="A thoughtful way forward")
    intro_heading = models.TextField(max_length=140, default="Your next chapter")
    intro_emphasis = models.CharField(max_length=80, default="starts here.")
    intro_body = models.TextField(
        max_length=500,
        default=(
            "Whether you are searching for your first home, exploring an investment, "
            "or simply learning your options, Lala Land helps make every next step feel clearer."
        ),
    )
    intro_cta = models.CharField(
        max_length=80,
        default="Tell me what you’re looking for",
    )

    resources_eyebrow = models.CharField(max_length=100, default="Homebuyer resources")
    resources_heading = models.TextField(max_length=140, default="Learn before you")
    resources_emphasis = models.CharField(max_length=80, default="make your move.")
    resources_cta = models.CharField(max_length=80, default="Explore all resources")

    final_cta_eyebrow = models.CharField(max_length=100, default="Begin your search")
    final_cta_heading = models.TextField(max_length=140, default="Ready to find what")
    final_cta_emphasis = models.CharField(max_length=80, default="feels like yours?")
    final_cta_label = models.CharField(max_length=80, default="Let’s find your next home")

    content_panels = Page.content_panels + [
        MultiFieldPanel(
            [
                FieldPanel("hero_eyebrow"),
                FieldPanel("hero_heading"),
                FieldPanel("hero_emphasis"),
                FieldPanel("hero_intro"),
                FieldPanel("hero_primary_cta"),
                FieldPanel("hero_secondary_cta"),
            ],
            heading="Hero",
        ),
        MultiFieldPanel(
            [
                FieldPanel("intro_eyebrow"),
                FieldPanel("intro_heading"),
                FieldPanel("intro_emphasis"),
                FieldPanel("intro_body"),
                FieldPanel("intro_cta"),
            ],
            heading="Introduction",
        ),
        MultiFieldPanel(
            [
                FieldPanel("resources_eyebrow"),
                FieldPanel("resources_heading"),
                FieldPanel("resources_emphasis"),
                FieldPanel("resources_cta"),
            ],
            heading="Resources section",
        ),
        MultiFieldPanel(
            [
                FieldPanel("final_cta_eyebrow"),
                FieldPanel("final_cta_heading"),
                FieldPanel("final_cta_emphasis"),
                FieldPanel("final_cta_label"),
            ],
            heading="Final call to action",
        ),
    ]

    def get_context(self, request, *args, **kwargs):
        from apps.sitecontent.models import AboutPage, ArticlePage, ResourceIndexPage

        context = super().get_context(request, *args, **kwargs)
        context["featured_articles"] = (
            ArticlePage.objects.live()
            .public()
            .filter(featured=True, archived_at__isnull=True, category__active=True)
            .select_related("category", "cover_image")[:3]
        )
        context["resources_page"] = ResourceIndexPage.objects.live().public().first()
        context["about_page"] = AboutPage.objects.live().public().first()
        return context
