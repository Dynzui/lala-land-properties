from django.urls import path

from . import views

app_name = "access_requests"

urlpatterns = [
    path("", views.access_dashboard, name="dashboard"),
    path("request/", views.create_access_request, name="request"),
    path("requests/<uuid:request_id>/<str:decision>/", views.review_access_request, name="review"),
    path("grants/<uuid:grant_id>/revoke/", views.revoke_access_grant, name="revoke"),
    path("locations/<uuid:location_id>/private/", views.private_location, name="private_location"),
]
