from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django import forms
from .models import Attraction, VisitSlot, Booking, Profile, TicketDraw, TicketDrawBooking, TicketDrawVisitSlot
from .forms import BookingForm
from django.utils import timezone
import datetime
from django.db import transaction
from django.db.models import Q, F, Sum
from django.db.models.functions import Coalesce, Least
from django.utils.dateparse import parse_date
from django.contrib.admin.views.decorators import staff_member_required


User = get_user_model()

# Create your views here.

@staff_member_required
def admin_dashboard(request):
    """
    Tier A (Lightweight Version): Admin Workbench Page
    - Statistics: Active Draws / Open Venues / Bookings / Pending Requests
    - Entry Point: Redirects to Django Admin or an existing page
    - Permissions: Staff only
    """
    now = timezone.now()

    # TicketDraw.is_open / Attraction.is_open are Python methods and cannot be directly filtered by an ORM, so sum + iteration is used.
    active_draws_count = sum(1 for d in TicketDraw.objects.all() if d.is_open(now))
    open_venues_count = sum(1 for a in Attraction.objects.all() if a.is_open(now))

    bookings_count = Booking.objects.filter(cancelled=False).count()
    pending_requests_count = TicketDrawBooking.objects.filter(cancelled=False).count()

    return render(
        request,
        "fergusonbequest/admin_dashboard.html",
        {
            "active_draws_count": active_draws_count,
            "open_venues_count": open_venues_count,
            "bookings_count": bookings_count,
            "pending_requests_count": pending_requests_count,
        },
    )


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

@login_required
def ticket_draws_view(request):
    draws = TicketDraw.objects.all().order_by("name")

    selected = None
    date_range = None

    selected_id = request.GET.get("draw")
    if selected_id:
        selected = get_object_or_404(TicketDraw, pk=selected_id)

        # Try to compute date range from visit slots
        # If not, fall back to fields on TicketDraw (start/end or draw_date).
        try:
            slots = TicketDrawVisitSlot.objects.filter(ticket_draw=selected).order_by("date")
            if slots.exists():
                first_date = slots.first().date
                last_date = slots.last().date
                if first_date == last_date:
                    date_range = first_date.strftime("%d/%m/%Y")
                else:
                    date_range = f"{first_date.strftime('%d/%m/%Y')} – {last_date.strftime('%d/%m/%Y')}"
        except Exception:
            start_date = getattr(selected, "start_date", None)
            end_date = getattr(selected, "end_date", None)
            draw_date = getattr(selected, "draw_date", None)

            if draw_date:
                try:
                    date_range = draw_date.strftime("%d/%m/%Y")
                except Exception:
                    date_range = str(draw_date)
            elif start_date and end_date:
                try:
                    if start_date == end_date:
                        date_range = start_date.strftime("%d/%m/%Y")
                    else:
                        date_range = f"{start_date.strftime('%d/%m/%Y')} – {end_date.strftime('%d/%m/%Y')}"
                except Exception:
                    date_range = f"{start_date} – {end_date}"

    return render(request, "fergusonbequest/ticket_draws.html", {
        "draws": draws,
        "selected": selected,
        "date_range": date_range,
    })


@login_required
def ticket_draw_detail(request, slug):
    draw = get_object_or_404(TicketDraw, slug=slug)

    # Count user's current entries to fit the limits
    existing_entries = TicketDrawBooking.objects.filter(
        user=request.user,
        ticket_draw=draw,
        cancelled=False
    ).count()

    remaining_allowance = max(0, draw.per_year_limit - existing_entries)

    if request.method == 'POST':
        # prevent multiple bookings for same draw
        # Check if user already has any active booking for this draw
        if existing_entries > 0:
            messages.error(request, f"You already have an active entry for {draw.name}. You must cancel your existing entry before booking a different date or adding tickets.")
            return redirect('waiting_list')
        num_tickets = int(request.POST.get('num_tickets', 1))

        # Error if they exceed their draw limit
        if num_tickets > remaining_allowance:
            messages.error(request, f"Max limit reached. You can only choose up to {remaining_allowance} more tickets.")
            return redirect('ticket_draw_detail', slug=slug)

        slot_id = request.POST.get('slot_id')
        slot = get_object_or_404(TicketDrawVisitSlot, pk=slot_id)

        if slot.remaining >= num_tickets and draw.is_open():
            with transaction.atomic():
                TicketDrawBooking.objects.create(
                    user=request.user,
                    ticket_draw=draw,
                    slot=slot,
                    num_tickets=num_tickets,
                    full_name=f"{request.user.first_name} {request.user.last_name}",
                    email=request.user.email,
                    agreed_terms=True
                )
                slot.remaining = F('remaining') - num_tickets
                slot.save()
            messages.success(request, "Successfully entered draw!")
            return redirect('waiting_list')

    slots = TicketDrawVisitSlot.objects.filter(
        ticket_draw=draw,
        date__gte=timezone.now().date()
    ).order_by("date", "time")

    return render(request, "fergusonbequest/ticket_draw_detail.html", {
        "draw": draw,
        "slots": slots,
        "remaining_allowance": remaining_allowance
    })

@login_required
def cancel_ticket_draw_entry(request, pk):
    """Allows a user to cancel their own ticket draw entry and restores slot capacity."""
    # Ensure the user owns this booking before allowing cancellation
    booking = get_object_or_404(TicketDrawBooking, pk=pk, user=request.user)

    if request.method == 'POST':
        with transaction.atomic():
            if not booking.cancelled:
                booking.cancelled = True
                booking.save()
                # Add tickets back to the TicketDrawVisitSlot
                slot = booking.slot
                slot.remaining = F('remaining') + booking.num_tickets
                slot.save()
            messages.success(request, f"Entry for {booking.ticket_draw.name} cancelled.")

    return redirect('waiting_list')
def logout_view(request):
    """Log the user out and redirect to home.
    """
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('home')

def terms(request):
    return render(request, 'fergusonbequest/terms.html')


def attraction(request, pk):
    """Show attraction detail and available future slots."""
    attraction = get_object_or_404(Attraction, pk=pk)

    available_slots = VisitSlot.objects.filter(
        attraction=attraction,
        date__gte=timezone.now().date()
    ).order_by("date", "time")

    year = timezone.now().year
    used = Booking.objects.filter(
        user=request.user,
        cancelled=False,
        created_at__year=year
    ).count()

    remaining_allowance = max(0, 3 - used)

    return render(request, 'fergusonbequest/attraction.html', {
        'attraction': attraction,
        'available_slots': available_slots,
        'remaining_allowance': remaining_allowance,
    })

def attractions_view(request):
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()

    date_str = request.GET.get("date", "").strip()
    d = parse_date(date_str) if date_str else None

    location = request.GET.get("location", "").strip()
    sort = request.GET.get("sort", "name").strip()

    attractions = (
        Attraction.objects
        .annotate(tickets_left_total=Coalesce(Sum("slots__remaining"), 0))
    )

    if q:
        attractions = attractions.filter(
            Q(name__icontains=q) |
            Q(location__icontains=q)
        )

    if status == "available":
        attractions = attractions.filter(tickets_left_total__gt=0)
    elif status == "soldout":
        attractions = attractions.filter(tickets_left_total=0)

    if location:
        attractions = attractions.filter(location__iexact=location)

    if d:
        attractions = attractions.filter(
            slots__date__gte=d,
            slots__remaining__gt=0
        ).distinct()

    if sort == "tickets":
        attractions = attractions.order_by("-tickets_left_total", "name")
    else:
        attractions = attractions.order_by("name")

    locations = Attraction.objects.values_list("location", flat=True).distinct().order_by("location")

    return render(request, "fergusonbequest/attractions.html", {
        "attractions": attractions,
        "q": q,
        "status": status,
        "date": date_str,
        "location_filter": location,
        "sort": sort,
        "locations": locations,
        "types": [],
        "type_filter": "",
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


@login_required
def waiting_list(request):
    user = request.user
    # Get all draws
    ticket_draws = TicketDraw.objects.all().order_by("name")

    # Get user's active bookings
    user_bookings = TicketDrawBooking.objects.filter(
        user=user,
        cancelled=False
    ).select_related('slot', 'ticket_draw')

    # Create a map: Draw ID -> Booking Object
    bookings_map = {b.ticket_draw_id: b for b in user_bookings}

    for d in ticket_draws:
        # Check if this draw exists in the user's bookings
        if d.id in bookings_map:
            d.user_booking = bookings_map[d.id]  # Attach the booking object
            d.joined = True
        else:
            d.user_booking = None
            d.joined = False

    return render(request, "fergusonbequest/waiting_list.html", {
        "ticket_draws": ticket_draws,
    })