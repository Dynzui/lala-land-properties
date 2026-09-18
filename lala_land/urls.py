from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from two_factor.urls import urlpatterns as two_factor_urlpatterns
from wagtail import urls as wagtail_urls
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.documents import urls as wagtaildocs_urls

from apps.properties.views import geography_data
from apps.accounts.views import admin_login_redirect
from apps.dashboard.views import cms_dashboard
from search import views as search_views

urlpatterns = [
    path(
        "",
        include(
            (two_factor_urlpatterns[0], "two_factor"),
            namespace="two_factor",
        ),
    ),
    path("django-admin/", admin.site.urls),
    path("staff/access/", include("apps.access_requests.urls")),
    path("staff/", include("apps.accounts.urls")),
    path("properties/", include("apps.listings.urls")),
    path("contact/", include("apps.inquiries.urls")),
    path("admin/login/", admin_login_redirect, name="admin_login_redirect"),
    path("admin/", cms_dashboard, name="lala_cms_dashboard"),
    path("admin/", include(wagtailadmin_urls)),
    path("documents/", include(wagtaildocs_urls)),
    path("search/", search_views.search, name="search"),
    path("geography/", geography_data, name="philippine_geography"),
]


if settings.DEBUG:
    from django.conf.urls.static import static
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    # Serve static and media files from development server
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns = urlpatterns + [
    # For anything not caught by a more specific rule above, hand over to
    # Wagtail's page serving mechanism. This should be the last pattern in
    # the list:
    path("", include(wagtail_urls)),
    # Alternatively, if you want Wagtail pages to be served from a subpath
    # of your site, rather than the site root:
    #    path("pages/", include(wagtail_urls)),
]
