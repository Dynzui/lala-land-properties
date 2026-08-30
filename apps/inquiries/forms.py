from django import forms

from .models import Inquiry


class PublicInquiryForm(forms.ModelForm):
    website = forms.CharField(required=False, widget=forms.HiddenInput)
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
            "name": forms.TextInput(attrs={"autocomplete": "name"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email"}),
            "phone": forms.TextInput(attrs={"autocomplete": "tel"}),
            "message": forms.Textarea(attrs={"rows": 5}),
        }

    def clean_website(self):
        if self.cleaned_data["website"]:
            raise forms.ValidationError("Unable to submit this inquiry.")
        return ""
