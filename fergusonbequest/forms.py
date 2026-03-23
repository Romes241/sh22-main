from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import get_user_model
from django.forms import ValidationError
from django.utils.text import slugify
from .models import Booking, VisitSlot, Attraction, TicketDraw, FeedbackEmailTemplate, BookingFeedback

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
            candidates = list(User.objects.filter(email__iexact=email.strip()).order_by('id'))

            if not candidates:
                raise forms.ValidationError(self.error_messages.get('invalid_login',
                    "Please ensure your email and password are correct."),
                    code='invalid_login')

            user_obj = None
            for candidate in candidates:
                if candidate.check_password(password):
                    user_obj = candidate
                    break

            if user_obj is None:
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


class FeedbackEmailTemplateForm(forms.ModelForm):
    """Form for editing the feedback email template."""

    def clean(self):
        cleaned_data = super().clean()
        mode = cleaned_data.get('feedback_mode')
        feedback_url = (cleaned_data.get('feedback_url') or '').strip()

        if mode == FeedbackEmailTemplate.FEEDBACK_MODE_EXTERNAL and not feedback_url:
            self.add_error(
                'feedback_url',
                'A Microsoft Forms URL is required when external feedback mode is selected.'
            )

        return cleaned_data
    
    class Meta:
        model = FeedbackEmailTemplate
        fields = [
            'enabled', 'feedback_mode', 'subject', 'body', 'feedback_url',
            'expiry_days', 'reminder_enabled', 'reminder_delay_days',
        ]
        widgets = {
            'feedback_mode': forms.Select(attrs={'class': 'form-control'}),
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'How was your visit to {attraction_name}?'
            }),
            'body': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 15,
                'placeholder': 'Dear {user_name},...'
            }),
            'feedback_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://forms.office.com/...'
            }),
            'expiry_days': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 90,
            }),
            'reminder_delay_days': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 30,
            }),
        }
        labels = {
            'enabled': 'Enable Feedback Emails',
            'feedback_mode': 'Feedback Collection Mode',
            'subject': 'Email Subject',
            'body': 'Email Message',
            'feedback_url': 'Microsoft Forms URL',
            'expiry_days': 'Submission Window (days)',
            'reminder_enabled': 'Enable Reminder Email',
            'reminder_delay_days': 'Reminder Delay (days)',
        }
        help_texts = {
            'enabled': 'Check this box to automatically send feedback emails to users after their visits.',
            'feedback_mode': 'Internal mode uses a secure in-app form. External mode uses the Microsoft Forms URL below.',
            'subject': 'Use {attraction_name}, {user_name}, {visit_date}, {feedback_url} as placeholders',
            'body': 'Available placeholders: {user_name}, {attraction_name}, {visit_date}, {feedback_url}',
            'feedback_url': 'Optional external URL. Leave blank to use the built-in feedback form link.',
            'expiry_days': 'Users can submit feedback until this many days after the visit ends.',
            'reminder_enabled': 'Send one reminder email if a user has not submitted feedback.',
            'reminder_delay_days': 'Number of days after the first feedback email before sending the reminder.',
        }


class BookingFeedbackForm(forms.ModelForm):
    class Meta:
        model = BookingFeedback
        fields = ['rating', 'comments']
        widgets = {
            'rating': forms.Select(
                choices=[(i, f'{i} / 5') for i in range(1, 6)],
                attrs={'class': 'form-control'}
            ),
            'comments': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 6,
                    'placeholder': 'Tell us about your experience (optional).',
                }
            ),
        }
