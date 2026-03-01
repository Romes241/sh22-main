import calendar
import csv
import random
from operator import itemgetter

from django import forms
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.db import IntegrityError, transaction
from django.db.models import Q, F, Sum, Count
from django.db.models.functions import Coalesce, Least
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST
from .forms_discount_codes import DiscountCodeForm
from django.views.decorators.http import require_http_methods
from openpyxl import Workbook
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.utils import get_column_letter

from .forms import (
    BookingForm,
    AttractionCreateForm,
    TicketDrawCreateForm,
    EmailAuthenticationForm,
)
from .forms_suggestions import AttractionSuggestionForm
from .models import (
    Attraction,
    VisitSlot,
    Booking,
    Profile,
    TicketDraw,
    TicketDrawBooking,
    TicketDrawVisitSlot,
    AttractionSuggestion,
    DiscountCode,
)

User = get_user_model()

# Business rule: max 3 bookings per calendar year (regular) and 3 per year (weekly_event) unless overridden elsewhere.
MAX_ATTRACTIONS_PER_YEAR = 3


# -----------------------------
# Small helpers / utilities
# -----------------------------
def _call_is_open(obj, now):
    """
    Supports both signatures:
      - obj.is_open()
      - obj.is_open(now)
    """
    if not hasattr(obj, "is_open"):
        return None
    try:
        return obj.is_open(now)
    except TypeError:
        return obj.is_open()


def calculate_remaining_allowance(user, attraction_type="regular"):
    """
    attraction_type:
      - 'regular'      -> Booking against Attraction
      - 'weekly_event' -> TicketDrawBooking against TicketDraw
    """
    year = timezone.now().year

    if attraction_type == "regular":
        used = Booking.objects.filter(
            user=user,
            cancelled=False,
            created_at__year=year,
            attraction__attraction_type="regular",
        ).count()
        return max(0, MAX_ATTRACTIONS_PER_YEAR - used)

    if attraction_type == "weekly_event":
        used = TicketDrawBooking.objects.filter(
            user=user,
            cancelled=False,
            created_at__year=year,
            ticket_draw__attraction_type="weekly_event",
        ).count()
        return max(0, MAX_ATTRACTIONS_PER_YEAR - used)

    return 0


def add_events(objects, events_by_day, start, end, event_type):
    """Add booking_open / booking_close events for calendar display."""
    for obj in objects:
        for field, class_name in [("booking_open", "booking-open"), ("booking_close", "booking-close")]:
            date_value = getattr(obj, field, None)
            if not date_value:
                continue
            event_date = date_value.date()
            if start <= event_date <= end:
                events_by_day.setdefault(event_date.day, []).append(
                    {"class_name": class_name, "object": obj, "event_type": event_type}
                )


def get_calendar(year=None, month=None):
    """
    Build calendar data for dashboard/calendar template rendering.
    Returns a dict (NOT a rendered response), so it can be merged into context via **calendar_data.
    """
    today = timezone.localdate()
    year = int(year or today.year)
    month = int(month or today.month)

    # prev / next nav
    if month == 1:
        prev_month, prev_year = 12, year - 1
    else:
        prev_month, prev_year = month - 1, year

    if month == 12:
        next_month, next_year = 1, year + 1
    else:
        next_month, next_year = month + 1, year

    cal = calendar.Calendar(firstweekday=0)
    month_days = list(cal.itermonthdates(year, month))
    start, end = month_days[0], month_days[-1]

    events_by_day = {}
    add_events(Attraction.objects.all(), events_by_day, start, end, "attraction")
    add_events(TicketDraw.objects.all(), events_by_day, start, end, "ticket_draw")

    weeks = []
    for i in range(0, len(month_days), 7):
        week = month_days[i : i + 7]
        week_info = []
        for day in week:
            day_events = events_by_day.get(day.day, []) if day.month == month else []
            week_info.append({"date": day, "events": day_events})
        weeks.append(week_info)

    return {
        "year": year,
        "month": month,
        "month_name": calendar.month_name[month],
        "weeks": weeks,
        "today": today,
        "prev_year": prev_year,
        "prev_month": prev_month,
        "next_year": next_year,
        "next_month": next_month,
    }


def assign_next_winner(draw: TicketDraw):
    """
    If current winner entry is cancelled/missing then pick a new winner from active entries.
    If no active entries then clear winner.
    """
    if getattr(draw, "winner_booking", None) and not draw.winner_booking.cancelled:
        return

    entries = list(
        TicketDrawBooking.objects.filter(ticket_draw=draw, cancelled=False).select_related("user")
    )

    if not entries:
        draw.winner_booking = None
        draw.winner_selected_at = None
    else:
        draw.winner_booking = random.choice(entries)
        draw.winner_selected_at = timezone.now()

    draw.save(update_fields=["winner_booking", "winner_selected_at"])


# -----------------------------
# Auth
# -----------------------------
class CustomLoginView(LoginView):
    template_name = "fergusonbequest/login.html"
    authentication_form = EmailAuthenticationForm

    def get_success_url(self):
        return reverse_lazy("home")


class RegistrationForm(forms.ModelForm):
    """Registration form for User. Unique email, password confirmation, auto-username."""

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
        user = super().save(commit=False)

        first = (self.cleaned_data.get("first_name") or "").strip()
        last = (self.cleaned_data.get("last_name") or "").strip()

        if first or last:
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
        user.set_password(self.cleaned_data.get("password"))

        if commit:
            user.save()
        return user


def register_view(request):
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


@require_POST
def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("home")


# -----------------------------
# Public / Home / Dashboard / Calendar / Terms
# -----------------------------
def home(request):
    attractions_qs = Attraction.objects.all().order_by("name")[:4]

    featured_attractions = [
        {
            "title": attr.name,
            "subtitle": (attr.description[:100] if attr.description else (attr.location or "Book now to visit")),
            "image": (attr.image.name if getattr(attr, "image", None) else "fergusonbequest/img/placeholder.jpg"),
            "id": attr.id,
            "url": f"/attraction/{attr.id}/book/",
        }
        for attr in attractions_qs
    ]

    # fallback if DB empty (helps tests/first run)
    if not featured_attractions:
        featured_attractions = [
            {"title": "Blair Drummond Safari Park", "subtitle": "Safari and adventure park.",
             "image": "fergusonbequest/img/blair_drumond.jpg", "id": None, "url": "/attractions/"},
            {"title": "Glasgow Clan Ice Hockey", "subtitle": "The city's professional hockey team.",
             "image": "fergusonbequest/img/glasgow_clan.jpg", "id": None, "url": "/attractions/"},
            {"title": "Edinburgh Zoo", "subtitle": "Scotland's most famous zoo.",
             "image": "fergusonbequest/img/edinburgh_zoo.jpg", "id": None, "url": "/attractions/"},
            {"title": "Ghostbusters Screening", "subtitle": "Who you gonna call?",
             "image": "fergusonbequest/img/ghostbusters.jpg", "id": None, "url": "/attractions/"},
        ]

    if request.user.is_authenticated:
        return render(
            request,
            "fergusonbequest/home_logged_in.html",
            {"featured_attractions": featured_attractions},
        )

    return render(request, "fergusonbequest/home.html", {"featured_attractions": featured_attractions})


@login_required
def dashboard_view(request, year=None, month=None):
    attractions_qs = Attraction.objects.all().order_by("name")[:4]

    featured_attractions = [
        {
            "title": attr.name,
            "subtitle": (attr.description[:100] if attr.description else (attr.location or "Book now to visit")),
            "image": (attr.image.name if getattr(attr, "image", None) else "fergusonbequest/img/placeholder.jpg"),
            "id": attr.id,
            "url": f"/attraction/{attr.id}/book/",
        }
        for attr in attractions_qs
    ]

    if not featured_attractions:
        featured_attractions = [
            {"title": "Blair Drummond Safari Park", "subtitle": "Safari and adventure park.",
             "image": "fergusonbequest/img/blair_drumond.jpg", "id": None, "url": "/attractions/"},
            {"title": "Glasgow Clan Ice Hockey", "subtitle": "The city's professional hockey team.",
             "image": "fergusonbequest/img/glasgow_clan.jpg", "id": None, "url": "/attractions/"},
            {"title": "Edinburgh Zoo", "subtitle": "Scotland's most famous zoo.",
             "image": "fergusonbequest/img/edinburgh_zoo.jpg", "id": None, "url": "/attractions/"},
            {"title": "Ghostbusters Screening", "subtitle": "Who you gonna call?",
             "image": "fergusonbequest/img/ghostbusters.jpg", "id": None, "url": "/attractions/"},
        ]

    calendar_data = get_calendar(year, month)
    return render(
        request,
        "fergusonbequest/dashboard.html",
        {"featured_attractions": featured_attractions, **calendar_data},
    )


def calendar_view(request, year=None, month=None):
    context = get_calendar(year, month)
    return render(request, "fergusonbequest/calendar.html", context)


def terms(request):
    return render(request, "fergusonbequest/terms.html")


# -----------------------------
# Attractions (user)
# -----------------------------
def attractions_view(request):
    q = (request.GET.get("q") or "").strip()
    status = (request.GET.get("status") or "").strip()

    date_str = (request.GET.get("date") or "").strip()
    d = parse_date(date_str) if date_str else None

    location = (request.GET.get("location") or "").strip()
    sort = (request.GET.get("sort") or "name").strip()

    today = timezone.now().date()

    attractions = (
        Attraction.objects.annotate(
            future_slots_count=Count("slots", filter=Q(slots__date__gte=today), distinct=True),
            tickets_left_total=Coalesce(Sum("slots__remaining", filter=Q(slots__date__gte=today)), 0),
        )
        .filter(future_slots_count__gt=0)
        .distinct()
    )

    if q:
        attractions = attractions.filter(Q(name__icontains=q) | Q(location__icontains=q))

    if status == "available":
        attractions = attractions.filter(tickets_left_total__gt=0)
    elif status == "soldout":
        attractions = attractions.filter(tickets_left_total=0)

    if location:
        attractions = attractions.filter(location__iexact=location)

    if d:
        attractions = attractions.filter(slots__date__gte=d).distinct()

    if sort == "tickets":
        attractions = attractions.order_by("-tickets_left_total", "name")
    else:
        attractions = attractions.order_by("name")

    locations = Attraction.objects.values_list("location", flat=True).distinct().order_by("location")

    return render(
        request,
        "fergusonbequest/attractions.html",
        {
            "attractions": attractions,
            "q": q,
            "status": status,
            "date": date_str,
            "location_filter": location,
            "sort": sort,
            "locations": locations,
            "types": [],
            "type_filter": "",
        },
    )


def attraction(request, pk):
    attraction_obj = get_object_or_404(Attraction, pk=pk)

    available_slots = VisitSlot.objects.filter(
        attraction=attraction_obj,
        date__gte=timezone.now().date(),
    ).order_by("date", "time")

    remaining_allowance = 0
    if request.user.is_authenticated:
        remaining_allowance = calculate_remaining_allowance(request.user, attraction_obj.attraction_type)

    return render(
        request,
        "fergusonbequest/attraction.html",
        {
            "attraction": attraction_obj,
            "available_slots": available_slots,
            "remaining_allowance": remaining_allowance,
        },
    )


@login_required
def booking_view(request, attraction_pk):
    attraction_obj = get_object_or_404(Attraction, pk=attraction_pk)
    user = request.user

    available_slots = VisitSlot.objects.filter(
        attraction=attraction_obj,
        date__gte=timezone.now().date(),
    ).order_by("date", "time")

    booking_summary = {"price": "Free"}
    remaining_allowance = calculate_remaining_allowance(user, "regular")

    def redirect_to_history_with(msg):
        messages.error(request, msg)
        return redirect("booking_history")

    # GET
    if request.method == "GET":
        if remaining_allowance <= 0:
            return redirect_to_history_with(
                f"You have reached your yearly limit of {MAX_ATTRACTIONS_PER_YEAR} attractions. "
                "Please cancel/delete an existing booking in Booking History before booking again."
            )

        slot_id = request.GET.get("slot")
        if slot_id and not available_slots.filter(pk=slot_id).exists():
            return redirect_to_history_with("Invalid slot selected for this attraction.")

        if slot_id:
            already = Booking.objects.filter(user=user, slot_id=slot_id, cancelled=False).exists()
            if already:
                return redirect_to_history_with(
                    "Oops — you already have a booking for this time slot. "
                    "Please cancel it in Booking History before booking again."
                )

        form = BookingForm(attraction=attraction_obj, initial={"slot": slot_id} if slot_id else None)
        return render(
            request,
            "fergusonbequest/booking_page.html",
            {
                "attraction": attraction_obj,
                "available_slots": available_slots,
                "form": form,
                "booking_summary": booking_summary,
                "remaining_allowance": remaining_allowance,
                "max_allowance": MAX_ATTRACTIONS_PER_YEAR,
                "now": timezone.now(),
            },
        )

    # POST
    form = BookingForm(request.POST, attraction=attraction_obj)
    if not form.is_valid():
        return render(
            request,
            "fergusonbequest/booking_page.html",
            {
                "attraction": attraction_obj,
                "available_slots": available_slots,
                "form": form,
                "booking_summary": booking_summary,
                "remaining_allowance": remaining_allowance,
                "max_allowance": MAX_ATTRACTIONS_PER_YEAR,
                "now": timezone.now(),
            },
        )

    # Re-check allowance (safety)
    remaining_allowance = calculate_remaining_allowance(user, "regular")
    if remaining_allowance <= 0:
        return redirect_to_history_with(
            f"You have reached your yearly limit of {MAX_ATTRACTIONS_PER_YEAR} attractions. "
            "Please cancel/delete an existing booking in Booking History before booking again."
        )

    booking = form.save(commit=False)
    booking.user = user
    booking.attraction = attraction_obj
    booking.full_name = f"{user.first_name} {user.last_name}".strip()
    booking.email = user.email

    if booking.slot.attraction_id != attraction_obj.id:
        return redirect_to_history_with("Invalid slot selected for this attraction.")

    already = Booking.objects.filter(user=user, slot=booking.slot, cancelled=False).exists()
    if already:
        return redirect_to_history_with(
            "Oops — you already have a booking for this time slot. "
            "Please cancel it in Booking History before booking again."
        )

    try:
        with transaction.atomic():
            slot = VisitSlot.objects.select_for_update().get(pk=booking.slot.pk)
            if slot.remaining < booking.num_tickets:
                form.add_error("slot", "Not enough tickets remaining for this slot.")
                return render(
                    request,
                    "fergusonbequest/booking_page.html",
                    {
                        "attraction": attraction_obj,
                        "available_slots": available_slots,
                        "form": form,
                        "booking_summary": booking_summary,
                        "remaining_allowance": remaining_allowance,
                        "max_allowance": MAX_ATTRACTIONS_PER_YEAR,
                        "now": timezone.now(),
                    },
                )

            booking.save()
            VisitSlot.objects.filter(pk=slot.pk).update(remaining=F("remaining") - booking.num_tickets)

        messages.success(request, "Booking confirmed!")
        return redirect("booking_history")

    except IntegrityError:
        return redirect_to_history_with(
            "Duplicate booking detected for this time slot. Please cancel it in Booking History before booking again."
        )


@login_required
def booking_history(request):
    user = request.user
    remaining_allowance = calculate_remaining_allowance(user, "regular")

    bookings = Booking.objects.filter(user=user).select_related("slot", "attraction")
    draw_bookings = TicketDrawBooking.objects.filter(user=user).select_related("slot", "ticket_draw")

    when = request.GET.get("when")  # all|future|past|cancelled
    status = request.GET.get("status")  # all|active|cancelled
    venue = request.GET.get("venue")
    q = request.GET.get("q")
    start = request.GET.get("start")
    end = request.GET.get("end")
    sort = request.GET.get("sort", "created_at")

    today = timezone.now().date()

    if status == "cancelled":
        bookings = bookings.filter(cancelled=True)
        draw_bookings = draw_bookings.filter(cancelled=True)
    elif status == "active":
        bookings = bookings.filter(cancelled=False)
        draw_bookings = draw_bookings.filter(cancelled=False)

    if when == "future":
        bookings = bookings.filter(slot__date__gte=today)
        draw_bookings = draw_bookings.filter(slot__date__gte=today)
    elif when == "past":
        bookings = bookings.filter(slot__date__lt=today)
        draw_bookings = draw_bookings.filter(slot__date__lt=today)
    elif when == "cancelled":
        bookings = bookings.filter(cancelled=True)
        draw_bookings = draw_bookings.filter(cancelled=True)

    if venue:
        if venue.isdigit():
            bookings = bookings.filter(attraction__id=venue)
            draw_bookings = draw_bookings.filter(ticket_draw__id=venue)
        else:
            bookings = bookings.filter(attraction__slug__icontains=venue)
            draw_bookings = draw_bookings.filter(ticket_draw__slug__icontains=venue)

    if q:
        bookings = bookings.filter(
            Q(attraction__name__icontains=q)
            | Q(id__icontains=q)
            | Q(email__icontains=q)
            | Q(ticket_code__icontains=q)
        )
        draw_bookings = draw_bookings.filter(
            Q(ticket_draw__name__icontains=q)
            | Q(id__icontains=q)
            | Q(email__icontains=q)
            | Q(ticket_code__icontains=q)
        )

    sd = parse_date(start) if start else None
    ed = parse_date(end) if end else None
    if sd:
        bookings = bookings.filter(slot__date__gte=sd)
        draw_bookings = draw_bookings.filter(slot__date__gte=sd)
    if ed:
        bookings = bookings.filter(slot__date__lte=ed)
        draw_bookings = draw_bookings.filter(slot__date__lte=ed)

    future_bookings = list(bookings.filter(slot__date__gte=today))
    future_draws = list(draw_bookings.filter(slot__date__gte=today))
    past_bookings = list(bookings.filter(slot__date__lt=today))
    past_draws = list(draw_bookings.filter(slot__date__lt=today))

    for b in future_bookings + past_bookings:
        b.booking_type = "attraction"
        b.is_draw = False
    for d in future_draws + past_draws:
        d.booking_type = "draw"
        d.is_draw = True

    if sort == "slot_date":
        def sort_key(item):
            return (item.slot.date, item.created_at)
        reverse_sort = False
    else:
        def sort_key(item):
            return item.created_at
        reverse_sort = True

    future_all = sorted(future_bookings + future_draws, key=sort_key, reverse=reverse_sort)
    past_all = sorted(past_bookings + past_draws, key=sort_key, reverse=reverse_sort)

    return render(
        request,
        "fergusonbequest/booking_history.html",
        {
            "future_bookings": future_all,
            "past_bookings": past_all,
            "when": when,
            "status": status,
            "venue": venue,
            "q": q,
            "start": start,
            "end": end,
            "sort": sort,
            "now": timezone.now(),
            "remaining_allowance": remaining_allowance,
            "max_allowance": MAX_ATTRACTIONS_PER_YEAR,
        },
    )


@require_POST
@login_required
def cancel_booking(request, pk):
    """Cancel a future booking and restore slot capacity."""
    booking = get_object_or_404(Booking, pk=pk)

    if not (request.user == booking.user or request.user.is_superuser):
        return redirect("booking_history")

    if booking.slot.date < timezone.now().date():
        return redirect("booking_history")

    with transaction.atomic():
        b = Booking.objects.select_for_update().get(pk=booking.pk)

        if not b.cancelled:
            b.cancelled = True
            b.save(update_fields=["cancelled"])

            VisitSlot.objects.filter(pk=b.slot.pk).update(
                remaining=Least(F("remaining") + b.num_tickets, F("capacity"))
            )

            current_year = timezone.now().year
            active_yearly_count = Booking.objects.filter(
                user=b.user, cancelled=False, created_at__year=current_year
            ).count()
            remaining = max(0, MAX_ATTRACTIONS_PER_YEAR - active_yearly_count)

            messages.success(
                request,
                f"Booking cancelled. You now have {remaining}/{MAX_ATTRACTIONS_PER_YEAR} bookings remaining for this year.",
            )

    return redirect("booking_history")


# -----------------------------
# Ticket draws (user)
# -----------------------------
@login_required
def ticket_draws_view(request):
    draws = TicketDraw.objects.all().order_by("name")

    selected = None
    date_range = None

    selected_id = request.GET.get("draw")
    if selected_id:
        selected = get_object_or_404(TicketDraw, pk=selected_id)

        slots = TicketDrawVisitSlot.objects.filter(ticket_draw=selected).order_by("date")
        if slots.exists():
            first_date = slots.first().date
            last_date = slots.last().date
            if first_date == last_date:
                date_range = first_date.strftime("%d/%m/%Y")
            else:
                date_range = f"{first_date.strftime('%d/%m/%Y')} – {last_date.strftime('%d/%m/%Y')}"
        else:
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
                    date_range = (
                        start_date.strftime("%d/%m/%Y")
                        if start_date == end_date
                        else f"{start_date.strftime('%d/%m/%Y')} – {end_date.strftime('%d/%m/%Y')}"
                    )
                except Exception:
                    date_range = f"{start_date} – {end_date}"

    return render(
        request,
        "fergusonbequest/ticket_draws.html",
        {"draws": draws, "selected": selected, "date_range": date_range},
    )


@login_required
def ticket_draw_detail(request, slug):
    draw = get_object_or_404(TicketDraw, slug=slug)

    existing_entries = TicketDrawBooking.objects.filter(
        user=request.user,
        ticket_draw=draw,
        cancelled=False,
    ).count()

    remaining_allowance = calculate_remaining_allowance(
        request.user, getattr(draw, "attraction_type", "weekly_event")
    )
    draw_limit = getattr(draw, "per_year_limit", MAX_ATTRACTIONS_PER_YEAR)
    draw_specific_remaining = max(0, draw_limit - existing_entries)
    remaining_allowance = min(remaining_allowance, draw_specific_remaining)

    if request.method == "POST":
        if existing_entries > 0:
            messages.error(
                request,
                f"You already have an active entry for {draw.name}. "
                "You must cancel your existing entry before booking a different date or adding tickets.",
            )
            return redirect("draw_waiting_list")

        num_tickets = int(request.POST.get("num_tickets", 1))
        if num_tickets > remaining_allowance:
            messages.error(request, f"Max limit reached. You can only choose up to {remaining_allowance} more tickets.")
            return redirect("ticket_draw_detail", slug=slug)

        slot_id = request.POST.get("slot_id")
        if not slot_id:
            messages.error(request, "No available dates for this draw. Please check back later.")
            return redirect("ticket_draw_detail", slug=slug)

        slot = TicketDrawVisitSlot.objects.filter(pk=slot_id, ticket_draw=draw).first()
        if slot is None:
            messages.error(request, "Selected date is no longer available. Please choose another date.")
            return redirect("ticket_draw_detail", slug=slug)

        # check draw open
        if not _call_is_open(draw, timezone.now()):
            messages.error(request, "This draw is currently closed.")
            return redirect("ticket_draw_detail", slug=slug)

        if slot.remaining < num_tickets:
            messages.error(request, "Not enough availability for that date.")
            return redirect("ticket_draw_detail", slug=slug)

        with transaction.atomic():
            TicketDrawBooking.objects.create(
                user=request.user,
                ticket_draw=draw,
                slot=slot,
                num_tickets=num_tickets,
                full_name=f"{request.user.first_name} {request.user.last_name}",
                email=request.user.email,
                agreed_terms=True,
            )
            TicketDrawVisitSlot.objects.filter(pk=slot.pk).update(remaining=F("remaining") - num_tickets)

        messages.success(request, "Successfully entered draw!")
        return redirect("draw_waiting_list")

    slots = TicketDrawVisitSlot.objects.filter(
        ticket_draw=draw,
        date__gte=timezone.now().date(),
    ).order_by("date", "time")

    return render(
        request,
        "fergusonbequest/ticket_draw_detail.html",
        {"draw": draw, "slots": slots, "remaining_allowance": remaining_allowance},
    )


@login_required
def draw_waiting_list(request):
    """Pending draw entries for the user; highlights winner needing action."""
    user = request.user
    now = timezone.now()

    entries = (
        TicketDrawBooking.objects.filter(user=user, cancelled=False, is_accepted=False)
        .select_related("ticket_draw", "slot")
        .order_by("-created_at")
    )

    for e in entries:
        is_winner = getattr(e.ticket_draw, "winner_booking_id", None) == e.id
        if is_winner and getattr(e, "is_accepted", False):
            e.ui_status = "Accepted"
        elif is_winner:
            e.ui_status = "Winner (Action required)"
        else:
            e.ui_status = "Waiting for draw"

        close = getattr(e.ticket_draw, "booking_close", None)
        e.can_cancel = (not getattr(e, "is_accepted", False)) and (not is_winner) and bool(close and now <= close)

    return render(request, "fergusonbequest/draw_waiting_list.html", {"entries": entries, "now": now})


# Compatibility alias (older routes may still point here)
@login_required
def waiting_list(request):
    return redirect("draw_waiting_list")


@require_POST
@login_required
def cancel_ticket_draw_entry(request, pk):
    booking = get_object_or_404(TicketDrawBooking, pk=pk, user=request.user)

    if getattr(booking, "is_accepted", False):
        messages.error(request, "You can't cancel an accepted draw win. Please contact support.")
        return redirect("draw_waiting_list")

    with transaction.atomic():
        if not booking.cancelled:
            booking.cancelled = True
            booking.save(update_fields=["cancelled"])

            TicketDrawVisitSlot.objects.filter(pk=booking.slot_id).update(
                remaining=F("remaining") + booking.num_tickets
            )

            draw = booking.ticket_draw
            if getattr(draw, "winner_booking_id", None) == booking.id:
                draw.winner_booking = None
                draw.winner_selected_at = None
                draw.save(update_fields=["winner_booking", "winner_selected_at"])
                assign_next_winner(draw)

            messages.success(request, f"Entry for {draw.name} cancelled.")
        else:
            messages.info(request, "This entry was already cancelled.")

    return redirect(request.META.get("HTTP_REFERER", "draw_waiting_list"))


@require_POST
@login_required
def accept_draw_win(request, pk):
    booking = get_object_or_404(TicketDrawBooking, pk=pk, user=request.user)
    draw = booking.ticket_draw

    if getattr(draw, "winner_booking_id", None) == booking.id:
        booking.is_accepted = True
        booking.save(update_fields=["is_accepted"])
        messages.success(request, f"You have officially accepted your tickets for {draw.name}!")
    else:
        messages.error(request, "You are not the current winner of this draw.")

    return redirect("booking_history")


@require_POST
@login_required
def decline_draw_win(request, pk):
    booking = get_object_or_404(TicketDrawBooking, pk=pk, user=request.user)
    draw = booking.ticket_draw

    if getattr(draw, "winner_booking_id", None) != booking.id:
        messages.error(request, "Invalid request.")
        return redirect("draw_waiting_list")

    with transaction.atomic():
        if not booking.cancelled:
            booking.cancelled = True
            booking.save(update_fields=["cancelled"])
            TicketDrawVisitSlot.objects.filter(pk=booking.slot_id).update(
                remaining=F("remaining") + booking.num_tickets
            )

        draw.winner_booking = None
        draw.winner_selected_at = None
        draw.save(update_fields=["winner_booking", "winner_selected_at"])

        assign_next_winner(draw)

    messages.info(request, "You have declined the tickets. A new winner has been selected.")
    return redirect("draw_waiting_list")


# -----------------------------
# Waiting list for attractions (session-based)
# -----------------------------
@login_required
def waiting_listattraction(request):
    attractions = Attraction.objects.all().order_by("name")
    joined_ids = set(request.session.get("attraction_waitlist_ids", []))

    for a in attractions:
        a.joined = a.id in joined_ids

    return render(request, "fergusonbequest/waiting_listattraction.html", {"attractions": attractions})


@require_POST
@login_required
def waiting_listattraction_join(request, pk):
    attraction_obj = get_object_or_404(Attraction, pk=pk)

    ids = set(request.session.get("attraction_waitlist_ids", []))
    ids.add(attraction_obj.id)
    request.session["attraction_waitlist_ids"] = list(ids)

    messages.success(request, f"You joined the waiting list for {attraction_obj.name}.")
    return redirect("waiting_listattraction")


@require_POST
@login_required
def waiting_listattraction_leave(request, pk):
    attraction_obj = get_object_or_404(Attraction, pk=pk)

    ids = set(request.session.get("attraction_waitlist_ids", []))
    ids.discard(attraction_obj.id)
    request.session["attraction_waitlist_ids"] = list(ids)

    messages.success(request, f"You left the waiting list for {attraction_obj.name}.")
    return redirect("waiting_listattraction")


# -----------------------------
# Suggestions (user) + export (staff)
# -----------------------------
@login_required
def create_attraction_suggestion(request):
    if request.method == "POST":
        form = AttractionSuggestionForm(request.POST)
        if form.is_valid():
            suggestion = form.save(commit=False)
            suggestion.submitted_by = request.user
            suggestion.save()
            messages.success(request, "Suggestion submitted successfully.")
            # prevents duplicate submit on refresh
            return redirect("create_attraction_suggestion")
        messages.error(request, "Please fix the errors below and try again.")
    else:
        form = AttractionSuggestionForm()

    return render(
        request,
        "fergusonbequest/attraction_suggestion_page.html",
        {"form": form},
    )


@staff_member_required
def export_suggestions_excel(request):
    qs = (
        AttractionSuggestion.objects
        .select_related("submitted_by")
        .order_by("-created_at")
    )

    wb = Workbook()
    ws = wb.active
    ws.title = "Attraction Suggestions"

    headers = [
        "Name",
        "Location",
        "Website URL",
        "Description",
        "Why Recommended",
        "Status",
        "Submitted By",
        "Created At",
    ]
    ws.append(headers)

    for s in qs:
        ws.append([
            s.name,
            getattr(s, "location", "") or "",
            getattr(s, "website_url", "") or "",
            getattr(s, "description", "") or "",
            getattr(s, "why_recommended", "") or "",
            getattr(s, "status", "") or "",
            (s.submitted_by.username if s.submitted_by else ""),
            s.created_at.strftime("%Y-%m-%d %H:%M") if getattr(s, "created_at", None) else "",
        ])

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{ws.max_row}"

    dv = DataValidation(
        type="list",
        formula1='"Pending,In progress,Implemented,Rejected"',
        allow_blank=True
    )
    ws.add_data_validation(dv)
    if ws.max_row >= 2:
        dv.add(f"F2:F{ws.max_row}")

    for col_idx in range(1, len(headers) + 1):
        col_letter = get_column_letter(col_idx)
        max_len = 0
        for cell in ws[col_letter]:
            value = "" if cell.value is None else str(cell.value)
            max_len = max(max_len, len(value))
        ws.column_dimensions[col_letter].width = min(max_len + 2, 55)

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="attraction_suggestions.xlsx"'
    wb.save(response)
    return response


# -----------------------------
# Discount Codes (staff page)
# -----------------------------
@staff_member_required
@require_http_methods(["GET", "POST"])
def discount_codes_page(request):
    now = timezone.now()

    if request.method == "POST":
        form = DiscountCodeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Discount code created.")
            return redirect("discount_codes")
        messages.error(request, "Please fix the errors below.")
    else:
        form = DiscountCodeForm()

    all_discounts = DiscountCode.objects.all().order_by("-created_at")

    active_discounts = all_discounts.filter(
        is_active=True,
        valid_from__lte=now,
        valid_until__gte=now,
    )

    return render(
        request,
        "fergusonbequest/discount_codes.html",
        {
            "form": form,
            "active_discounts": active_discounts,
            "all_discounts": all_discounts,
            "now": now,
        },
    )

# -----------------------------
# Staff / Admin dashboard + management
# -----------------------------
@staff_member_required
def admin_dashboard(request):
    now = timezone.now()

    active_draws_count = sum(1 for d in TicketDraw.objects.all() if _call_is_open(d, now))
    open_venues_count = sum(1 for a in Attraction.objects.all() if _call_is_open(a, now))

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


@staff_member_required
def admin_management(request):
    tab = request.GET.get("tab", "draws")
    q = (request.GET.get("q") or "").strip()

    sort_draws = request.GET.get("sort_draws", "close_date_desc")
    sort_attractions = request.GET.get("sort_attractions", "date_desc")

    draws_qs = TicketDraw.objects.all()
    attractions_qs = Attraction.objects.all()

    if q:
        draws_qs = draws_qs.filter(name__icontains=q)
        attractions_qs = attractions_qs.filter(name__icontains=q)

    if sort_draws == "open_first":
        draws_qs = draws_qs.order_by("-booking_open", "-booking_close", "name")
    elif sort_draws == "close_date":
        draws_qs = draws_qs.order_by("booking_close", "name")
    elif sort_draws == "close_date_desc":
        draws_qs = draws_qs.order_by("-booking_close", "name")
    else:
        draws_qs = draws_qs.order_by("name")

    if sort_attractions == "date":
        attractions_qs = attractions_qs.order_by("booking_open", "name")
    elif sort_attractions == "date_desc":
        attractions_qs = attractions_qs.order_by("-booking_open", "name")
    else:
        attractions_qs = attractions_qs.order_by("name")

    now = timezone.now()
    for d in draws_qs:
        d.is_open_now = bool(_call_is_open(d, now))
        d.is_closed_now = not d.is_open_now

    return render(
        request,
        "fergusonbequest/admin_management.html",
        {
            "draws": draws_qs,
            "attractions": attractions_qs,
            "tab": tab,
            "q": q,
            "sort_draws": sort_draws,
            "sort_attractions": sort_attractions,
        },
    )


# Compatibility alias: urls.py may expect management_view
@staff_member_required
def management_view(request):
    return admin_management(request)


@staff_member_required
@require_POST
def run_draw(request, draw_id):
    draw = get_object_or_404(TicketDraw, pk=draw_id)

    now = timezone.now()
    if _call_is_open(draw, now):
        messages.error(request, "This draw is still open. You can only run it after it closes.")
        return redirect(f"{reverse('admin_management')}?tab=draws")

    entries = list(
        TicketDrawBooking.objects.filter(ticket_draw=draw, cancelled=False).select_related("user")
    )

    if not entries:
        draw.winner_booking = None
        draw.winner_selected_at = None
        draw.save(update_fields=["winner_booking", "winner_selected_at"])
        messages.error(request, "No active entries for this draw.")
        return redirect(f"{reverse('admin_management')}?tab=draws")

    draw.winner_booking = random.choice(entries)
    draw.winner_selected_at = timezone.now()
    draw.save(update_fields=["winner_booking", "winner_selected_at"])

    winner = draw.winner_booking
    winner_name = winner.full_name or (winner.user.get_username() if winner.user else "Winner")

    messages.success(request, f"Winner selected: {winner_name}")
    return redirect(f"{reverse('admin_management')}?tab=draws")


@staff_member_required
@require_POST
def mng_delete_ticket_draw(request, draw_id):
    draw = get_object_or_404(TicketDraw, pk=draw_id)
    draw.delete()
    messages.success(request, "Draw deleted.")
    return redirect("/admin-dashboard/management/?tab=draws")


@staff_member_required
@require_POST
def mng_delete_draw(request, draw_id):
    # Backwards-compatible alias for older URL patterns/tests
    return mng_delete_ticket_draw(request, draw_id)


@staff_member_required
@require_POST
def mng_delete_attraction(request, attraction_id):
    attraction_obj = get_object_or_404(Attraction, pk=attraction_id)
    attraction_obj.delete()
    messages.success(request, "Attraction deleted.")
    return redirect("/admin-dashboard/management/?tab=attractions")


@staff_member_required
def create_attraction(request):
    if request.method == "POST":
        form = AttractionCreateForm(request.POST, request.FILES)
        if form.is_valid():
            attraction_obj = form.save()
            messages.success(request, f'Attraction "{attraction_obj.name}" created successfully!')
            return redirect("admin_dashboard")
    else:
        form = AttractionCreateForm()

    return render(
        request,
        "fergusonbequest/create_attraction.html",
        {"form": form, "title": "Create New Attraction"},
    )


@staff_member_required
def edit_attraction(request, pk):
    attraction_obj = get_object_or_404(Attraction, pk=pk)

    if request.method == "POST":
        form = AttractionCreateForm(request.POST, request.FILES, instance=attraction_obj)
        if form.is_valid():
            form.save()
            messages.success(request, f'Attraction "{attraction_obj.name}" updated successfully!')
            return redirect("admin_dashboard")
    else:
        form = AttractionCreateForm(instance=attraction_obj)

    return render(
        request,
        "fergusonbequest/edit_attraction.html",
        {"form": form, "title": "Edit Attraction", "attraction": attraction_obj},
    )


@staff_member_required
def create_ticket_draw(request):
    if request.method == "POST":
        form = TicketDrawCreateForm(request.POST, request.FILES)
        if form.is_valid():
            draw = form.save()
            messages.success(request, f'Ticket Draw "{draw.name}" created successfully!')
            return redirect("admin_dashboard")
    else:
        form = TicketDrawCreateForm()

    return render(
        request,
        "fergusonbequest/create_ticket_draw.html",
        {"form": form, "title": "Create New Ticket Draw"},
    )


@staff_member_required
def edit_ticket_draw(request, pk):
    draw = get_object_or_404(TicketDraw, pk=pk)

    if request.method == "POST":
        form = TicketDrawCreateForm(request.POST, request.FILES, instance=draw)
        if form.is_valid():
            form.save()
            messages.success(request, f'Ticket Draw "{draw.name}" updated successfully!')
            return redirect("admin_dashboard")
    else:
        form = TicketDrawCreateForm(instance=draw)

    return render(
        request,
        "fergusonbequest/edit_ticket_draw.html",
        {"form": form, "title": "Edit Ticket Draw", "ticket_draw": draw},
    )


# -----------------------------
# Staff tools (draw entry JSON etc.)
# -----------------------------
@staff_member_required
def staff_draws_entry(request):
    draws = TicketDraw.objects.all().order_by("-id")
    selected = draws.first()

    return render(
        request,
        "fergusonbequest/staff_draws_entry.html",
        {
            "draws": draws,
            "selected_draw": selected,
        },
    )


@staff_member_required
def staff_draw_json(request, pk: int):
    draw = get_object_or_404(TicketDraw, pk=pk)
    now = timezone.now()

    payload = {
        "id": draw.pk,
        "title": getattr(draw, "title", None) or getattr(draw, "name", None) or str(draw),
        "slug": getattr(draw, "slug", "") or "",
        "description": getattr(draw, "description", "") or "",
        "is_open": _call_is_open(draw, now),
    }

    return JsonResponse(payload)


# -----------------------------
# Reports (admin)
# -----------------------------
@staff_member_required
def admin_reports(request):
    name = request.GET.get("name")
    surname = request.GET.get("surname")
    guid = request.GET.get("guid")
    email = request.GET.get("email")
    start = request.GET.get("start")
    end = request.GET.get("end")
    venue = request.GET.get("venue")
    status = request.GET.get("status")
    q = request.GET.get("q")
    booking_type = request.GET.get("booking_type", "all")
    venue_select = request.GET.get("venue_select")
    specific_date = request.GET.get("specific_date")
    specific_time = request.GET.get("specific_time")
    date_select = request.GET.get("date_select")
    time_select = request.GET.get("time_select")

    sort = request.GET.get("sort", "newest")

    draw_qs = TicketDrawBooking.objects.select_related("user", "ticket_draw", "slot")
    attraction_qs = Booking.objects.select_related("user", "attraction", "slot")

    today = timezone.localdate()

    def apply_filters(qs_in, is_draw=True):
        qs_out = qs_in

        if name:
            qs_out = qs_out.filter(user__first_name__icontains=name)
        if surname:
            qs_out = qs_out.filter(user__last_name__icontains=surname)
        if guid:
            qs_out = qs_out.filter(user__username__icontains=guid)
        if email:
            qs_out = qs_out.filter(user__email__icontains=email)
        if start:
            qs_out = qs_out.filter(slot__date__gte=start)
        if end:
            qs_out = qs_out.filter(slot__date__lte=end)

        venue_value = venue if venue else venue_select
        if venue_value:
            if is_draw:
                qs_out = qs_out.filter(ticket_draw__name__icontains=venue_value)
            else:
                qs_out = qs_out.filter(attraction__name__icontains=venue_value)

        date_value = specific_date if specific_date else date_select
        if date_value:
            qs_out = qs_out.filter(slot__date=date_value)

        time_value = specific_time if specific_time else time_select
        if time_value:
            qs_out = qs_out.filter(slot__time=time_value)

        if status == "active":
            qs_out = qs_out.filter(cancelled=False, slot__date__gte=today)
        elif status == "cancelled":
            qs_out = qs_out.filter(cancelled=True)
        elif status == "completed":
            qs_out = qs_out.filter(cancelled=False, slot__date__lt=today)

        if q:
            common_filters = (
                Q(user__first_name__icontains=q)
                | Q(user__last_name__icontains=q)
                | Q(user__username__icontains=q)
                | Q(user__email__icontains=q)
                | Q(slot__date__icontains=q)
                | Q(slot__time__icontains=q)
            )
            if is_draw:
                qs_out = qs_out.filter(common_filters | Q(ticket_draw__name__icontains=q))
            else:
                qs_out = qs_out.filter(common_filters | Q(attraction__name__icontains=q))

        return qs_out

    combined = []
    if booking_type in ["all", "draw"]:
        for b in apply_filters(draw_qs, True):
            if b.cancelled:
                status_text = "Cancelled"
            elif b.slot.date < today:
                status_text = "Completed"
            else:
                status_text = "Active"

            combined.append(
                {
                    "type": "Draw",
                    "created": b.created_at,
                    "name": b.ticket_draw.name,
                    "first_name": b.user.first_name if b.user else "",
                    "last_name": b.user.last_name if b.user else "",
                    "guid": b.user.username if b.user else "",
                    "email": b.user.email if b.user else (b.email or ""),
                    "date": b.slot.date,
                    "time": b.slot.time,
                    "ticket_code": b.ticket_code,
                    "num_tickets": b.num_tickets,
                    "status_text": status_text,
                }
            )

    if booking_type in ["all", "attraction"]:
        for b in apply_filters(attraction_qs, False):
            if b.cancelled:
                status_text = "Cancelled"
            elif b.slot.date < today:
                status_text = "Completed"
            else:
                status_text = "Active"

            combined.append(
                {
                    "type": "Attraction",
                    "created": b.created_at,
                    "name": b.attraction.name,
                    "first_name": b.user.first_name if b.user else "",
                    "last_name": b.user.last_name if b.user else "",
                    "guid": b.user.username if b.user else "",
                    "email": b.user.email if b.user else (b.email or ""),
                    "date": b.slot.date,
                    "time": b.slot.time,
                    "ticket_code": b.ticket_code,
                    "num_tickets": b.num_tickets,
                    "status_text": status_text,
                }
            )

    combined.sort(key=itemgetter("created"), reverse=(sort == "newest"))

    # Pagination
    page = request.GET.get("page", 1)
    per_page = 20
    total_bookings = len(combined)
    total_pages = (total_bookings + per_page - 1) // per_page

    try:
        page = int(page)
        if page < 1:
            page = 1
        elif total_pages > 0 and page > total_pages:
            page = total_pages
    except (ValueError, TypeError):
        page = 1

    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_bookings = combined[start_idx:end_idx]

    export_type = request.GET.get("export")
    if export_type:
        headers = ["Type", "Attraction/Draw", "Forename", "Surname", "GUID", "Email", "Date", "Time", "Ticket Code", "Tickets", "Status"]

        if export_type == "csv":
            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = 'attachment; filename="reports.csv"'
            writer = csv.writer(response)
            writer.writerow(headers)
            for b in combined:
                writer.writerow(
                    [
                        b["type"],
                        b["name"],
                        b["first_name"],
                        b["last_name"],
                        b["guid"],
                        b["email"],
                        b["date"].strftime("%d/%m/%Y"),
                        b["time"].strftime("%H:%M") if b["time"] else "",
                        b["ticket_code"],
                        b["num_tickets"],
                        b["status_text"],
                    ]
                )
            return response

        if export_type == "excel":
            wb = Workbook()
            ws = wb.active
            ws.title = "Reports"

            ws.append(headers)
            for b in combined:
                ws.append(
                    [
                        b["type"],
                        b["name"],
                        b["first_name"],
                        b["last_name"],
                        b["guid"],
                        b["email"],
                        b["date"].strftime("%d/%m/%Y"),
                        b["time"].strftime("%H:%M") if b["time"] else "",
                        b["ticket_code"],
                        b["num_tickets"],
                        b["status_text"],
                    ]
                )

            response = HttpResponse(
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            response["Content-Disposition"] = 'attachment; filename="reports.xlsx"'
            wb.save(response)
            return response

    def calculate_statistics(bookings_list):
        total = len(bookings_list)
        attraction_count = sum(1 for b in bookings_list if b["type"] == "Attraction")
        draw_count = total - attraction_count

        active_count = sum(1 for b in bookings_list if b["status_text"] == "Active")
        completed_count = sum(1 for b in bookings_list if b["status_text"] == "Completed")
        cancelled_count = sum(1 for b in bookings_list if b["status_text"] == "Cancelled")

        total_tickets = sum(b.get("num_tickets", 0) for b in bookings_list)

        date_range = None
        if bookings_list:
            dates = [b["date"] for b in bookings_list]
            date_range = {"start": min(dates), "end": max(dates)}

        popularity = {}
        for b in bookings_list:
            popularity[b["name"]] = popularity.get(b["name"], 0) + 1

        most_popular = None
        if popularity:
            n, c = max(popularity.items(), key=lambda x: x[1])
            most_popular = {"name": n, "count": c}

        unique_users = len(set(b["email"] for b in bookings_list if b["email"]))
        avg_per_user = total / unique_users if unique_users > 0 else 0

        return {
            "total_bookings": total,
            "total_tickets": total_tickets,
            "attraction_count": attraction_count,
            "draw_count": draw_count,
            "active_count": active_count,
            "completed_count": completed_count,
            "cancelled_count": cancelled_count,
            "date_range": date_range,
            "most_popular": most_popular,
            "unique_users": unique_users,
            "avg_per_user": avg_per_user,
        }

    statistics = calculate_statistics(combined)

    venue_list = sorted({b["name"] for b in combined})
    date_list = sorted({b["date"] for b in combined}, reverse=True)
    time_list = sorted({b["time"] for b in combined if b["time"]})

    return render(
        request,
        "fergusonbequest/admin_reports.html",
        {
            "bookings": paginated_bookings,
            "selected_booking_type": booking_type,
            "selected_status": status,
            "statistics": statistics,
            "current_page": page,
            "total_pages": total_pages,
            "total_bookings": total_bookings,
            "has_previous": page > 1,
            "has_next": page < total_pages,
            "previous_page": page - 1,
            "next_page": page + 1,
            "page_range": range(1, total_pages + 1),
            "start_index": (start_idx + 1) if total_bookings else 0,
            "end_index": min(end_idx, total_bookings),
            "venue_list": venue_list,
            "date_list": date_list,
            "time_list": time_list,
        },
    )
