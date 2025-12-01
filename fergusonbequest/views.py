from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django import forms
from .models import Attraction, VisitSlot, Booking, Profile
from django.shortcuts import render

User = get_user_model()

# Create your views here.
def home(request):
    featured_attractions = [
        {
            "title": "Blair Drummond Safari Park",
            "subtitle": "Safari and adventure park.",
            "image": "fergusonbequest/img/blair_drumond.jpg",
            "url": "https://www.blairdrummond.com",
        },
        {
            "title": "Glasgow Clan Ice Hockey",
            "subtitle": "The city's professional hockey team.",
            "image": "fergusonbequest/img/glasgow_clan.jpg",
            "url": "https://clanihc.com",
        },
        {
            "title": "Edinburgh Zoo",
            "subtitle": "Scotland's most famous zoo.",
            "image": "fergusonbequest/img/edinburgh_zoo.jpg",
            "url": "https://www.edinburghzoo.org.uk",
        },
        {
            "title": "Ghostbusters Screening",
            "subtitle": "Who you gonna call?",
            "image": "fergusonbequest/img/ghostbusters.jpg",
            "url": "https://www.imdb.com/title/tt0087332/",
        },
    ]

    return render(
        request,
        "fergusonbequest/home.html",
        {"featured_attractions": featured_attractions},
    )

class RegistrationForm(forms.ModelForm):
    """Form for user registration, extending the User model. Cleans email and password then saves
    Also auto-generates a unique username based on FirstName + LastName or email local-part."""
    password = forms.CharField(widget=forms.PasswordInput, label="Password")
    password_confirm = forms.CharField(widget=forms.PasswordInput, label="Confirm Password")
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email")
    def clean(self):
        cleaned = super().clean()
        p = cleaned.get("password")
        pc = cleaned.get("password_confirm")
        if p and pc and p != pc:
            self.add_error("password_confirm", "Passwords do not match.")
        return cleaned
    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("A user with that email already exists.")
        return email
    def save(self, commit=True):
        """Create a User instance, auto-generate a unique username and set the password.

        We generate a username from the email local-part (before the @). If that
        username is already taken, append a counter until unique.
        """
        user = super().save(commit=False)
        # generate a base username from FirstName + LastName (e.g. JohnSmith)
        first = (self.cleaned_data.get("first_name") or "").strip()
        last = (self.cleaned_data.get("last_name") or "").strip()
        if first or last:
            # Capitalise first letters to produce e.g. JohnSmith
            base = f"{first.capitalize()}{last.capitalize()}"
        else:
            email = self.cleaned_data.get("email") or ""
            base = email.split("@")[0] if "@" in email else "user"
        base = base or "user"
        username = base
        counter = 0
        while User.objects.filter(username=username).exists():
            counter += 1
            username = f"{base}{counter}"
        user.username = username
        user.email = (self.cleaned_data.get("email") or "").strip().lower()
        # set the password from the cleaned data
        user.set_password(self.cleaned_data.get("password"))
        if commit:
            user.save()
        return user
    
def register_view(request):
    """Handle user registration."""
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Registration successful.")
            return redirect("home")
    else:
        form = RegistrationForm()
    return render(request, "fergusonbequest/register.html", {"form": form})

@login_required
def dashboard_view(request):
    return render(request, "fergusonbequest/dashboard.html")


def logout_view(request):
    """Log the user out and redirect to home.
    """
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('home')

