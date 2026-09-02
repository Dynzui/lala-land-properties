from django.urls import path

from .views import accept_invitation

app_name = "accounts"

urlpatterns = [path("invitations/accept/<str:token>/", accept_invitation, name="accept_invitation")]
