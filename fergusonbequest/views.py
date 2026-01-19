from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django import forms
from .models import Attraction, VisitSlot, Booking, Profile
from django.shortcuts import render
from .forms import BookingForm
from django.utils import timezone
from django.db.models import Q
import datetime
from django.db import transaction
from django.db.models import F
from django.db.models.functions import Least

User = get_user_model()

# Create your views here.
def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

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
    """Handle user registration and land new users on the dashboard.

    After creating and logging in a new user we redirect to the dashboard so
    they land in their personalised view (not the anonymous homepage).
    """
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Registration successful.")
            return redirect("dashboard")
    else:
        form = RegistrationForm()
    return render(request, "fergusonbequest/register.html", {"form": form})

@login_required
def dashboard_view(request):
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

    return render(request, "fergusonbequest/dashboard.html", {"featured_attractions": featured_attractions})


def logout_view(request):
    """Log the user out and redirect to home.
    """
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('home')

def terms(request):
    return render(request, 'fergusonbequest/terms.html')


def attraction_detail(request, pk):
    """Show attraction detail and available future slots."""
    attraction = get_object_or_404(Attraction, pk=pk)
    available_slots = VisitSlot.objects.filter(attraction=attraction, date__gte=timezone.now().date())
    return render(request, 'fergusonbequest/attraction_detail.html', {
        'attraction': attraction,
        'available_slots': available_slots,
    })

def booking_view(request, attraction_pk):
    attraction = get_object_or_404(Attraction, pk=attraction_pk)
    available_slots = VisitSlot.objects.filter(attraction=attraction, date__gte=timezone.now().date())
    booking_summary = {'price': 'Free'}
    if request.method == 'POST':
        form = BookingForm(request.POST, attraction=attraction)
        if form.is_valid():
            booking = form.save(commit=False)
            if request.user.is_authenticated:
                booking.user = request.user
            booking.attraction = attraction
            booking.save()
            # reduce slot remaining
            booking.slot.remaining = max(0, booking.slot.remaining - 1)
            booking.slot.save()
            return redirect('dashboard')
    else:
        form = BookingForm(attraction=attraction)

    return render(request, 'fergusonbequest/booking_page.html', {
        'attraction': attraction,
        'available_slots': available_slots,
        'form': form,
        'booking_summary': booking_summary,
    })


@login_required
def booking_history(request):
    """Show list of bookings for the logged in user."""
    user = request.user

    # Base queryset
    bookings = Booking.objects.filter(user=user).select_related('slot', 'attraction')

    # Parse GET params for filters
    when = request.GET.get('when')  # all|future|past
    status = request.GET.get('status')  # all|active|cancelled
    venue = request.GET.get('venue')
    q = request.GET.get('q')
    start = request.GET.get('start')
    end = request.GET.get('end')
    sort = request.GET.get('sort')

    today = timezone.now().date()

    if status == 'cancelled':
        bookings = bookings.filter(cancelled=True)
    elif status == 'active':
        bookings = bookings.filter(cancelled=False)

    if venue:
        if venue.isdigit():
            bookings = bookings.filter(attraction__pk=int(venue))
        else:
            bookings = bookings.filter(attraction__slug__icontains=venue)

    if q:
        bookings = bookings.filter(
            Q(attraction__name__icontains=q) | Q(id__icontains=q) | Q(email__icontains=q)
        )

    try:
        if start:
            sd = datetime.date.fromisoformat(start)
            bookings = bookings.filter(slot__date__gte=sd)
        if end:
            ed = datetime.date.fromisoformat(end)
            bookings = bookings.filter(slot__date__lte=ed)
    except ValueError:
        # ignore invalid dates
        pass

    # sorting is applied before splitting into past/future
    if sort == 'slot_date':
        bookings = bookings.order_by('slot__date', '-created_at')
    elif sort == 'created_at':
        bookings = bookings.order_by('-created_at')
    else:
        bookings = bookings.order_by('-created_at')

    # split into two querysets for template rendering
    future_bookings = bookings.filter(slot__date__gte=today)
    past_bookings = bookings.filter(slot__date__lt=today)

    return render(request, 'fergusonbequest/booking_history.html', {
        'future_bookings': future_bookings,
        'past_bookings': past_bookings,
        'when': when,
    })


@login_required
def cancel_booking(request, pk):
    """Allow the booking owner (or superuser) to cancel a future booking.
    """
    booking = get_object_or_404(Booking, pk=pk)

    # Only user or admin can cancel
    if not (request.user == booking.user or request.user.is_superuser):
        return redirect('booking_history')

    if booking.slot.date < timezone.now().date():
        return redirect('booking_history')

    if request.method == 'POST':
        with transaction.atomic():
            b = Booking.objects.select_for_update().get(pk=booking.pk)
            if not b.cancelled:
                b.cancelled = True
                b.save()
                VisitSlot.objects.filter(pk=b.slot.pk).update(
                    remaining=Least(F('remaining') + 1, F('capacity'))
                )
    return redirect('booking_history')