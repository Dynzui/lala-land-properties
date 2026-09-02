from django import forms

from .models import User


class StaffInvitationForm(forms.Form):
    email = forms.EmailField()
    role = forms.ChoiceField(choices=((User.Role.ADMIN, "Admin"), (User.Role.MAINTAINER, "Maintainer")))


class StaffRoleForm(forms.Form):
    role = forms.ChoiceField(choices=((User.Role.ADMIN, "Admin"), (User.Role.MAINTAINER, "Maintainer")))


class StaffStatusForm(forms.Form):
    status = forms.ChoiceField(choices=(
        (User.Status.ACTIVE, "Active"),
        (User.Status.SUSPENDED, "Suspended"),
        (User.Status.DISABLED, "Disabled"),
    ))


class AcceptStaffInvitationForm(forms.Form):
    full_name = forms.CharField(max_length=150, required=False)
    password = forms.CharField(widget=forms.PasswordInput)
    password_confirm = forms.CharField(widget=forms.PasswordInput)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password") != cleaned.get("password_confirm"):
            self.add_error("password_confirm", "Passwords do not match.")
        return cleaned
