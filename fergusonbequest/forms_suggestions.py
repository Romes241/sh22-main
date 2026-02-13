from django import forms
from .models import AttractionSuggestion

class AttractionSuggestionForm(forms.ModelForm):
    class Meta:
        model = AttractionSuggestion
        fields = ["name", "location", "website_url", "description", "why_recommended"]
        labels = {
            "name": "Attraction name",
            "location": "Location (optional)",
            "website_url": "Website URL (optional)",
            "description": "Description",
            "why_recommended": "Why do you recommend this?",
        }
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "e.g., Edinburgh Castle"}),
            "location": forms.TextInput(attrs={"placeholder": "e.g., Edinburgh"}),
            "website_url": forms.URLInput(attrs={"placeholder": "https://..."}),
            "description": forms.Textarea(attrs={"rows": 4, "placeholder": "Briefly describe the attraction..."}),
            "why_recommended": forms.Textarea(attrs={"rows": 4, "placeholder": "Explain why this would benefit staff..."}),
        }
