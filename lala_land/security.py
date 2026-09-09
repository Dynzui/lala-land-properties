from django.views.debug import SafeExceptionReporterFilter


class HardenedExceptionReporterFilter(SafeExceptionReporterFilter):
    """Keep request metadata and submitted form data out of error reports."""

    safe_meta_keys = frozenset(
        {
            "HTTP_ACCEPT",
            "HTTP_ACCEPT_LANGUAGE",
            "HTTP_HOST",
            "HTTP_REFERER",
            "HTTP_USER_AGENT",
            "PATH_INFO",
            "QUERY_STRING",
            "REMOTE_ADDR",
            "REQUEST_METHOD",
            "SERVER_NAME",
            "SERVER_PORT",
            "SERVER_PROTOCOL",
        }
    )

    def is_active(self, request):  # noqa: ARG002
        # Django's default filter switches off in DEBUG mode. Local error pages are
        # still viewed in a browser, so keep redaction active in every environment.
        return True

    def get_safe_request_meta(self, request):
        if not hasattr(request, "META"):
            return {}
        return {
            key: (
                self.cleanse_setting(key, value)
                if key in self.safe_meta_keys
                else self.cleansed_substitute
            )
            for key, value in request.META.items()
        }

    def get_post_parameters(self, request):
        if request is None or not hasattr(request, "POST"):
            return {}
        cleansed = request.POST.copy()
        for key in cleansed:
            cleansed[key] = self.cleansed_substitute
        return cleansed
