from django.contrib.auth.backends import ModelBackend

from .models import User


class RoleAwareAuthenticationBackend(ModelBackend):
    """Make Django authentication and admin entry respect account policy."""

    def user_can_authenticate(self, user):
        if user.status != User.Status.ACTIVE or not user.is_active:
            return False
        if user.role == User.Role.CUSTOMER:
            return False
        return super().user_can_authenticate(user)

    def has_perm(self, user_obj, perm, obj=None):
        if (
            perm == "wagtailadmin.access_admin"
            and user_obj.is_authenticated
            and user_obj.status == User.Status.ACTIVE
        ):
            return user_obj.role in {User.Role.OWNER, User.Role.ADMIN}
        return super().has_perm(user_obj, perm, obj=obj)
