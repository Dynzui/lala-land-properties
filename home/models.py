from wagtail.models import Page


class HomePage(Page):
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
