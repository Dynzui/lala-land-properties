from django.contrib import messages
from urllib.parse import urlencode

from django.shortcuts import redirect, render
from django.urls import reverse

from .forms import AcceptStaffInvitationForm
from .services import accept_staff_invitation


def admin_login_redirect(request):
    """Keep two-factor authentication as the only staff login entrance."""
    destination = request.GET.get("next") or "/admin/"
    query = urlencode({"next": destination})
    return redirect(f"{reverse('two_factor:login')}?{query}")


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
