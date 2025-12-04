from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import get_user_model

User = get_user_model()

class EmailAuthenticationForm(AuthenticationForm):
    """AuthenticationForm that accepts an email address in the username field.
    """
    error_messages = {
        'invalid_login': "Please ensure your email/password are correct.",
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
