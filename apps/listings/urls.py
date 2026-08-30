from django.urls import path

from . import views

app_name = "listings"

urlpatterns = [
    path("", views.listing_index, name="index"),
    path("inquire/<uuid:listing_id>/", views.listing_inquiry, name="inquiry"),
    path("<slug:slug>/", views.listing_detail, name="detail"),
]
