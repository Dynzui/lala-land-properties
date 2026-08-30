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
        if (
            perm.startswith("properties.")
            and user_obj.is_authenticated
            and user_obj.status == User.Status.ACTIVE
        ):
            action, _, model_name = perm.removeprefix("properties.").partition("_")
            if action == "delete":
                return False
            if user_obj.role == User.Role.OWNER:
                return action in {"add", "change", "view"}
            if user_obj.role == User.Role.ADMIN:
                if model_name == "location":
                    return action == "view"
                return action in {"add", "change", "view"}
        if (
            perm.startswith("listings.")
            and user_obj.is_authenticated
            and user_obj.status == User.Status.ACTIVE
        ):
            action, _, _model_name = perm.removeprefix("listings.").partition("_")
            if user_obj.role in {User.Role.OWNER, User.Role.ADMIN}:
                return action in {"add", "change", "view"}
        if (
            perm.startswith("inquiries.")
            and user_obj.is_authenticated
            and user_obj.status == User.Status.ACTIVE
        ):
            action, _, _model_name = perm.removeprefix("inquiries.").partition("_")
            if user_obj.role in {User.Role.OWNER, User.Role.ADMIN}:
                return action in {"add", "change", "view"}
        if (
            perm.startswith("media_library.")
            and user_obj.is_authenticated
            and user_obj.status == User.Status.ACTIVE
        ):
            action, _, _model_name = perm.removeprefix("media_library.").partition("_")
            if user_obj.role in {User.Role.OWNER, User.Role.ADMIN}:
                return action in {"add", "change", "view"}
        if (
            perm.startswith("sitecontent.")
            and user_obj.is_authenticated
            and user_obj.status == User.Status.ACTIVE
        ):
            action, _, _model_name = perm.removeprefix("sitecontent.").partition("_")
            if user_obj.role in {User.Role.OWNER, User.Role.ADMIN}:
                return action in {"add", "change", "view"}
        if (
            perm.startswith("wagtailimages.")
            and user_obj.is_authenticated
            and user_obj.status == User.Status.ACTIVE
        ):
            action, _, _model_name = perm.removeprefix("wagtailimages.").partition("_")
            if user_obj.role in {User.Role.OWNER, User.Role.ADMIN}:
                return action in {"add", "change", "view"}
        return super().has_perm(user_obj, perm, obj=obj)
