from django import template

from apps.sitecontent.models import AboutPage, ResourceIndexPage

register = template.Library()


@register.simple_tag
def sitecontent_pages():
    return {
        "about": AboutPage.objects.live().public().first(),
        "resources": ResourceIndexPage.objects.live().public().first(),
    }
