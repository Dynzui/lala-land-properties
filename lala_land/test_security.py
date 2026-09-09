from django.test import RequestFactory

from .security import HardenedExceptionReporterFilter


def test_exception_reporter_hides_environment_and_form_values():
    request = RequestFactory().post(
        "/contact/",
        {"email": "customer@example.test", "message": "Private inquiry"},
    )
    request.META["UNRELATED_ENVIRONMENT_VALUE"] = "credential-like-value"
    reporter_filter = HardenedExceptionReporterFilter()

    safe_meta = reporter_filter.get_safe_request_meta(request)
    safe_post = reporter_filter.get_post_parameters(request)

    assert safe_meta["PATH_INFO"] == "/contact/"
    assert safe_meta["UNRELATED_ENVIRONMENT_VALUE"] == reporter_filter.cleansed_substitute
    assert safe_post["email"] == reporter_filter.cleansed_substitute
    assert safe_post["message"] == reporter_filter.cleansed_substitute
