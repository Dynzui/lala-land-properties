from django import forms
from django.contrib.auth import get_user_model

from .models import Inquiry


class PublicInquiryForm(forms.ModelForm):
    website = forms.CharField(required=False, widget=forms.HiddenInput)
    budget = forms.IntegerField(
        required=False,
        min_value=1,
        label="Budget (₱)",
        widget=forms.NumberInput(
            attrs={
                "min": "1",
                "step": "1000",
                "inputmode": "numeric",
                "placeholder": "e.g. 3000000",
            }
        ),
    )
    consent = forms.BooleanField(
        label="I agree that Lala Land may use these details to respond to my inquiry."
    )

    class Meta:
        model = Inquiry
        fields = [
            "name",
            "email",
            "phone",
            "interest",
            "preferred_location",
            "budget",
            "timeline",
            "message",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={"autocomplete": "name", "placeholder": "Your full name"}
            ),
            "email": forms.EmailInput(
                attrs={"autocomplete": "email", "placeholder": "you@example.com"}
            ),
            "phone": forms.TextInput(
                attrs={"autocomplete": "tel", "placeholder": "+63 9xx xxx xxxx"}
            ),
            "preferred_location": forms.TextInput(attrs={"placeholder": "e.g. Bacolod"}),
            "timeline": forms.TextInput(attrs={"placeholder": "e.g. Within six months"}),
            "message": forms.Textarea(attrs={"rows": 5}),
        }

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get("email") and not cleaned_data.get("phone"):
            raise forms.ValidationError("Provide an email address or mobile number.")
        return cleaned_data

    def clean_website(self):
        if self.cleaned_data["website"]:
            raise forms.ValidationError("Unable to submit this inquiry.")
        return ""


class InquiryAdminForm(forms.ModelForm):
    class Meta:
        model = Inquiry
        fields = [
            "name",
            "email",
            "listing",
            "interest",
            "preferred_location",
            "budget",
            "timeline",
            "message",
            "status",
            "assigned_to",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user_model = get_user_model()
        self.fields["assigned_to"].queryset = user_model.objects.filter(
            status=user_model.Status.ACTIVE,
            role__in=[user_model.Role.OWNER, user_model.Role.ADMIN],
        ).order_by("first_name", "last_name", "email")
