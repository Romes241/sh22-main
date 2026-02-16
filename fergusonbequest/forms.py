from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import get_user_model
from django.forms import ValidationError
from django.utils.text import slugify
from .models import Booking, VisitSlot, Attraction, TicketDraw

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


class AttractionCreateForm(forms.ModelForm):
    """Form for creating a new Attraction by staff members."""
    
    short_description = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter Short Description',
            'class': 'form-control'
        }),
        help_text='Brief summary shown in listings'
    )
    
    class Meta:
        model = Attraction
        fields = [
            'name', 'location', 'image', 'description', 
            'contact_email', 'terms', 'booking_open', 
            'booking_close', 'per_year_limit'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'Enter Title',
                'class': 'form-control'
            }),
            'location': forms.TextInput(attrs={
                'placeholder': 'Enter Location',
                'class': 'form-control'
            }),
            'description': forms.Textarea(attrs={
                'placeholder': 'Enter Long Description',
                'class': 'form-control',
                'rows': 6
            }),
            'contact_email': forms.EmailInput(attrs={
                'placeholder': 'contact@example.com',
                'class': 'form-control'
            }),
            'terms': forms.Textarea(attrs={
                'placeholder': 'Enter terms and conditions',
                'class': 'form-control',
                'rows': 4
            }),
            'booking_open': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
            'booking_close': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
            'per_year_limit': forms.NumberInput(attrs={
                'placeholder': '3',
                'class': 'form-control',
                'min': '1'
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            })
        }
        labels = {
            'name': 'Attraction Title',
            'description': 'Long Description',
            'booking_open': 'Booking Opens',
            'booking_close': 'Booking Closes',
            'per_year_limit': 'Number of Tickets (Per User Per Year)',
            'image': 'Attraction Image'
        }
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if not instance.slug:
            instance.slug = slugify(instance.name)
        if commit:
            instance.save()
        return instance


class TicketDrawCreateForm(forms.ModelForm):
    """Form for creating a new Ticket Draw by staff members."""
    
    short_description = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter Short Description',
            'class': 'form-control'
        }),
        help_text='Brief summary shown in listings'
    )
    
    event_has_no_date = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Check if event has no date'
    )
    
    visible_to_staff = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Visible to staff'
    )
    
    class Meta:
        model = TicketDraw
        fields = [
            'name', 'location', 'image', 'description',
            'contact_email', 'terms', 'draw_date',
            'booking_open', 'booking_close', 'per_year_limit'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'Enter Title',
                'class': 'form-control'
            }),
            'location': forms.TextInput(attrs={
                'placeholder': 'Enter Location',
                'class': 'form-control'
            }),
            'description': forms.Textarea(attrs={
                'placeholder': 'Enter Long Description',
                'class': 'form-control',
                'rows': 6
            }),
            'contact_email': forms.EmailInput(attrs={
                'placeholder': 'contact@example.com',
                'class': 'form-control'
            }),
            'terms': forms.Textarea(attrs={
                'placeholder': 'Enter terms and conditions',
                'class': 'form-control',
                'rows': 4
            }),
            'draw_date': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
            'booking_open': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
            'booking_close': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
            'per_year_limit': forms.NumberInput(attrs={
                'placeholder': '3',
                'class': 'form-control',
                'min': '1'
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            })
        }
        labels = {
            'name': 'Draw Title',
            'description': 'Long Description',
            'draw_date': 'Draw Date',
            'booking_open': 'Booking Opens',
            'booking_close': 'Booking Closes',
            'per_year_limit': 'Number of Available Tickets',
            'image': 'Draw Image'
        }
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if not instance.slug:
            instance.slug = slugify(instance.name)
        if commit:
            instance.save()
        return instance
