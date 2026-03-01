from django import forms
from django.utils import timezone
from .models import DiscountCode


class DiscountCodeForm(forms.ModelForm):
    class Meta:
        model = DiscountCode
        fields = ("title", "code", "description", "valid_from", "valid_until", "is_active")
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # datetime-local (HTML5) for better UX
        self.fields["valid_from"].widget = forms.DateTimeInput(attrs={"type": "datetime-local"})
        self.fields["valid_until"].widget = forms.DateTimeInput(attrs={"type": "datetime-local"})

        # sensible default: active
        if self.instance.pk is None and "is_active" in self.fields:
            self.fields["is_active"].initial = True

    def clean(self):
        cleaned = super().clean()
        vf = cleaned.get("valid_from")
        vu = cleaned.get("valid_until")

        if vf and vu and vu <= vf:
            self.add_error("valid_until", "valid_until must be after valid_from.")

        # optional: prevent creating already-expired code
        # (comment out if you want to allow backdating)
        if vu and vu <= timezone.now():
            self.add_error("valid_until", "valid_until must be in the future.")

        return cleaned