from django.urls import path

from . import views

app_name = "inquiries"

urlpatterns = [
    path("", views.contact, name="contact"),
    path("sent/", views.success, name="success"),
    path("staff/<uuid:inquiry_id>/phone/", views.phone, name="phone"),
]
