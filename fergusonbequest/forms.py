from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import get_user_model
from django.forms import ValidationError
from .models import Booking, VisitSlot

User = get_user_model()

class EmailAuthenticationForm(AuthenticationForm):
    """AuthenticationForm that accepts an email address in the username field.
    """
    error_messages = {
        'invalid_login': "Please ensure your email and password are correct.",
    }
    username = forms.EmailField(label="Email", widget=forms.EmailInput(attrs={'autofocus': True}))

    def clean(self):
        cleaned_data = self.cleaned_data
        email = cleaned_data.get('username')
        password = cleaned_data.get('password')

        if email and password:
            try:
                user_obj = User.objects.get(email__iexact=email.strip())
            except User.DoesNotExist:
                raise forms.ValidationError(self.error_messages.get('invalid_login',
                    "Please ensure your email and password are correct."),
                    code='invalid_login')

            if not user_obj.check_password(password):
                raise forms.ValidationError(self.error_messages.get('invalid_login',
                    "Please ensure your email and password are correct."),
                    code='invalid_login')
            
            self.confirm_login_allowed(user_obj)
            self.user_cache = user_obj

        return cleaned_data

    def get_user(self):
        return getattr(self, 'user_cache', None)


class BookingForm(forms.ModelForm):
    """ModelForm to create a Booking.
    """
    class Meta:
        model = Booking
        fields = ( "slot","num_tickets", "agreed_terms")
        labels = {
            "num_tickets": "Number of tickets",
        }
    def __init__(self, *args, attraction=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Hide agreed_terms
        self.fields["agreed_terms"].widget = forms.HiddenInput()
        # Make num_tickets a dropdown limited to 1 or 2
        self.fields["num_tickets"].widget = forms.Select(choices=[(1, "1"), (2, "2")])

        if attraction is not None:
            self.fields['slot'].queryset = VisitSlot.objects.filter(attraction=attraction)

    def clean_agreed_terms(self):
        agreed = self.cleaned_data.get('agreed_terms')
        if not agreed:
            raise ValidationError('You must agree to the terms to complete the booking.')
        return agreed
