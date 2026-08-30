from django import forms

from .models import SensitiveAccessRequest


class SensitiveAccessRequestForm(forms.ModelForm):
    class Meta:
        model = SensitiveAccessRequest
        fields = ["scope", "location", "reason", "requested_minutes"]

    def clean(self):
        cleaned_data = super().clean()
        scope = cleaned_data.get("scope")
        location = cleaned_data.get("location")
        if scope == SensitiveAccessRequest.Scope.EXACT_LOCATION and location is None:
            self.add_error("location", "Choose the location you need to view.")
        if scope == SensitiveAccessRequest.Scope.PHONE_NUMBER:
            cleaned_data["location"] = None
        return cleaned_data


class SensitiveAccessReviewForm(forms.Form):
    review_note = forms.CharField(max_length=500, required=False, widget=forms.Textarea)
