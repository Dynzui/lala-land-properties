from django.contrib import messages
from django.shortcuts import redirect, render

from .forms import AcceptStaffInvitationForm
from .services import accept_staff_invitation


def accept_invitation(request, token):
    form = AcceptStaffInvitationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            accept_staff_invitation(
                token=token,
                password=form.cleaned_data["password"],
                full_name=form.cleaned_data["full_name"],
            )
        except ValueError as error:
            form.add_error(None, str(error))
        else:
            messages.success(request, "Your staff account is ready. Sign in to continue.")
            return redirect("two_factor:login")
    return render(request, "accounts/accept_invitation.html", {"form": form})
