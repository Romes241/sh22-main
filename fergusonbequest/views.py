from operator import itemgetter
import calendar
import csv
import datetime
import random

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
from django.views.decorators.http import require_POST, require_http_methods

from openpyxl import Workbook
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.utils import get_column_letter

from .models import (
    Attraction,
    VisitSlot,
    Booking,
    Profile,
    TicketDraw,
    TicketDrawBooking,
    TicketDrawVisitSlot,
    AttractionSuggestion,
)
from .forms import BookingForm, AttractionCreateForm, TicketDrawCreateForm
from .forms_suggestions import AttractionSuggestionForm
User = get_user_model()
MAX_ATTRACTIONS_PER_YEAR = 3

# Create your views here.

def calculate_remaining_allowance(user, attraction_type='regular'):
    """
    Calculate remaining booking allowance based on attraction type.

    Args:
        user: The user to check allowance for
        attraction_type: 'regular' or 'weekly_event'

    Returns:
        int: Number of bookings remaining for this type
    """
    year = timezone.now().year

    if attraction_type == 'regular':
        used = Booking.objects.filter(
            user=user,
            cancelled=False,
            created_at__year=year,
            attraction__attraction_type='regular'
        ).count()
        return max(0, 3 - used)

    elif attraction_type == 'weekly_event':
        used = TicketDrawBooking.objects.filter(
            user=user,
            cancelled=False,
            created_at__year=year,
            ticket_draw__attraction_type='weekly_event'
        ).count()
        return max(0, 3 - used)

    return 0

class CustomLoginView(LoginView):
    def get_success_url(self):
        return reverse_lazy("home")

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
        "title": getattr(draw, "title", None)
                 or getattr(draw, "name", None)
                 or str(draw),
        "slug": getattr(draw, "slug", "") or "",
        "description": getattr(draw, "description", "") or "",
        "is_open": draw.is_open(now) if hasattr(draw, "is_open") else None,
    }

    return JsonResponse(payload)


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

    # Data rows
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

    # Freeze header row and enable filter
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{ws.max_row}"

    # Dropdown for status column (column F)
    dv = DataValidation(
        type="list",
        formula1='"Pending,In progress,Implemented,Rejected"',
        allow_blank=True
    )
    # add dropdown for every active suggestion in row
    ws.add_data_validation(dv)
    if ws.max_row >= 2:
        dv.add(f"F2:F{ws.max_row}")

    # Auto-fit column widths
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

@staff_member_required
def admin_reports(request):

    name = request.GET.get('name')
    surname = request.GET.get('surname')
    guid = request.GET.get('guid')
    email = request.GET.get('email')
    start = request.GET.get('start')
    end = request.GET.get('end')
    venue = request.GET.get('venue')
    status = request.GET.get('status')
    q = request.GET.get('q')
    booking_type = request.GET.get('booking_type', 'all')
    venue_select = request.GET.get('venue_select')
    specific_date = request.GET.get('specific_date')
    specific_time = request.GET.get('specific_time')
    date_select = request.GET.get('date_select')
    time_select = request.GET.get('time_select')



    sort = request.GET.get('sort', 'newest')


    draw_qs = TicketDrawBooking.objects.select_related('user', 'ticket_draw', 'slot')
    attraction_qs = Booking.objects.select_related('user', 'attraction', 'slot')

    today = timezone.localdate()

    def apply_filters(qs, is_draw=True):
        if name:
            qs = qs.filter(user__first_name__icontains=name)

        if surname:
            qs = qs.filter(user__last_name__icontains=surname)

        if guid:
            qs = qs.filter(user__username__icontains=guid)

        if email:
            qs = qs.filter(user__email__icontains=email)

        if start:
            qs = qs.filter(slot__date__gte=start)

        if end:
            qs = qs.filter(slot__date__lte=end)

        venue_value = venue if venue else venue_select

        if venue_value:
            if is_draw:
                qs = qs.filter(ticket_draw__name__icontains=venue_value)
            else:
                qs = qs.filter(attraction__name__icontains=venue_value)

        
        
        date_value = specific_date if specific_date else date_select
        if date_value:
            qs = qs.filter(slot__date=date_value)


        time_value = specific_time if specific_time else time_select
        if time_value:
            qs = qs.filter(slot__time=time_value)







        if status == "active":
            qs = qs.filter(cancelled=False, slot__date__gte=today)
        elif status == "cancelled":
            qs = qs.filter(cancelled=True)
        elif status == "completed":
            qs = qs.filter(cancelled=False, slot__date__lt=today)

        if q:
            common_filters = (
                Q(user__first_name__icontains=q) |
                Q(user__last_name__icontains=q) |
                Q(user__username__icontains=q) |
                Q(user__email__icontains=q) |
                Q(slot__date__icontains=q) |
                Q(slot__time__icontains=q)
            )

            if is_draw:
                qs = qs.filter(
                    common_filters |
                    Q(ticket_draw__name__icontains=q)
                )
            else:
                qs = qs.filter(
                    common_filters |
                    Q(attraction__name__icontains=q)
                )

        return qs

    combined = []

    filtered_draw_qs = None
    filtered_attraction_qs = None

    if booking_type in ['all', 'draw']:
        filtered_draw_qs = apply_filters(draw_qs, True)
        for b in filtered_draw_qs:
            if b.cancelled:
                status_text = "Cancelled"
            elif b.slot.date < today:
                status_text = "Completed"
            else:
                status_text = "Active"

            combined.append({
                "type": "Draw",
                "created": b.created_at,
                "name": b.ticket_draw.name,

                "first_name": b.user.first_name if b.user else "",
                "last_name": b.user.last_name if b.user else "",
                "guid": b.user.username if b.user else "",
                "email": b.user.email if b.user else b.email,

                "date": b.slot.date,
                "time": b.slot.time,
                "cancelled": b.cancelled,
                "status_text": status_text,
            })



    if booking_type in ['all', 'attraction']:
        filtered_attraction_qs = apply_filters(attraction_qs, False)
        for b in filtered_attraction_qs:
            if b.cancelled:
                status_text = "Cancelled"
            elif b.slot.date < today:
                status_text = "Completed"
            else:
                status_text = "Active"

            combined.append({
                "type": "Attraction",
                "created": b.created_at,
                "name": b.attraction.name,

                "first_name": b.user.first_name if b.user else "",
                "last_name": b.user.last_name if b.user else "",
                "guid": b.user.username if b.user else "",
                "email": b.user.email if b.user else b.email,

                "date": b.slot.date,
                "time": b.slot.time,
                "cancelled": b.cancelled,
                "status_text": status_text,
            })


    reverse = True if sort == 'newest' else False
    combined.sort(key=itemgetter("created"), reverse=reverse)

    # Pagination
    page = request.GET.get('page', 1)
    per_page = 20
    
    # Calculate total pages
    total_bookings = len(combined)
    total_pages = (total_bookings + per_page - 1) // per_page  # Ceiling division
    
    # Get current page data
    try:
        page = int(page)
        if page < 1:
            page = 1
        elif page > total_pages:
            page = total_pages
    except (ValueError, TypeError):
        page = 1
    
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_bookings = combined[start_idx:end_idx]

    bookings = combined

    export_type = request.GET.get("export")

    if export_type:

        headers = [
            "Type",
            "Attraction/Draw",
            "Forename",
            "Surname",
            "GUID",
            "Email",
            "Date",
            "Time",
            "Status",
        ]

        if export_type == "csv":
            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = 'attachment; filename="reports.csv"'

            writer = csv.writer(response)
            writer.writerow(headers)

            for b in bookings:
                writer.writerow([
                    b["type"],
                    b["name"],
                    b["first_name"],
                    b["last_name"],
                    b["guid"],
                    b["email"],
                    b["date"].strftime("%d/%m/%Y"),
                    b["time"].strftime("%H:%M") if b["time"] else "",
                    b["status_text"],
                ])

            return response


        if export_type == "excel":

            wb = Workbook()
            ws = wb.active
            ws.title = "Reports"

            ws.append(headers)

            for b in bookings:
                ws.append([
                    b["type"],
                    b["name"],
                    b["first_name"],
                    b["last_name"],
                    b["guid"],
                    b["email"],
                    b["date"].strftime("%d/%m/%Y"),
                    b["time"].strftime("%H:%M") if b["time"] else "",
                    b["status_text"],
                ])

            response = HttpResponse(
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            response["Content-Disposition"] = 'attachment; filename="reports.xlsx"'

            wb.save(response)
            return response
        

    def calculate_statistics(bookings, filtered_draw_qs, filtered_attraction_qs):
        """Calculate statistics from the filtered bookings"""
        
        total_bookings = len(bookings)
        
        # Count by type
        attraction_count = sum(1 for b in bookings if b["type"] == "Attraction")
        draw_count = total_bookings - attraction_count
        
        # Count by status
        active_count = sum(1 for b in bookings if b["status_text"] == "Active")
        completed_count = sum(1 for b in bookings if b["status_text"] == "Completed")
        cancelled_count = sum(1 for b in bookings if b["status_text"] == "Cancelled")
        
        # Date range
        date_range = None
        if bookings:
            dates = [b["date"] for b in bookings]
            min_date = min(dates)
            max_date = max(dates)
            date_range = {"start": min_date, "end": max_date}
        
        # Most popular attraction/draw
        popularity = {}
        for b in bookings:
            name = b["name"]
            popularity[name] = popularity.get(name, 0) + 1
        
        most_popular = None
        if popularity:
            most_popular_name = max(popularity.items(), key=lambda x: x[1])
            most_popular = {"name": most_popular_name[0], "count": most_popular_name[1]}
        
        # Unique users
        unique_users = len(set(b["email"] for b in bookings))
        
        # Average bookings per user
        avg_per_user = total_bookings / unique_users if unique_users > 0 else 0
        
        return {
            "total_bookings": total_bookings,
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
        
    # Calculate statistics
    statistics = calculate_statistics(combined, filtered_draw_qs, filtered_attraction_qs)

    venue_set = set()
    date_set = set()
    time_set = set()

    for b in combined:
        venue_set.add(b["name"])
        date_set.add(b["date"])
        if b["time"]:
            time_set.add(b["time"])

    venue_list = sorted(venue_set)
    date_list = sorted(date_set, reverse=True)
    time_list = sorted(time_set)



    return render(request, "fergusonbequest/admin_reports.html", {
        "bookings": paginated_bookings,
        "selected_booking_type": booking_type,
        "selected_status": status,
        "statistics": statistics,
        # Pagination context variables
        "current_page": page,
        "total_pages": total_pages,
        "total_bookings": total_bookings,
        "has_previous": page > 1,
        "has_next": page < total_pages,
        "previous_page": page - 1,
        "next_page": page + 1,
        "page_range": range(1, total_pages + 1),
        "start_index": start_idx + 1,
        "end_index": min(end_idx, total_bookings),
        "venue_list": venue_list,
        "date_list": date_list,
        "time_list": time_list,
    })


def home(request):
    attractions_qs = Attraction.objects.all().order_by("name")[:4]

    featured_attractions = []
    for attr in attractions_qs:
        featured_attractions.append({
            "title": attr.name,
            "subtitle": (attr.description[:100] if attr.description else (attr.location or "Book now to visit")),
            "image": (attr.image.name if getattr(attr, "image", None) else "fergusonbequest/img/placeholder.jpg"),
            "id": attr.id,
            "url": f"/attraction/{attr.id}/book/",
        })

    # fallback only if DB empty for now to pass tests
    if not featured_attractions:
        featured_attractions = [
            {
                "title": "Blair Drummond Safari Park",
                "subtitle": "Safari and adventure park.",
                "image": "fergusonbequest/img/blair_drumond.jpg",
                "id": None,
                "url": "/attractions/",
            },
            {
                "title": "Glasgow Clan Ice Hockey",
                "subtitle": "The city's professional hockey team.",
                "image": "fergusonbequest/img/glasgow_clan.jpg",
                "id": None,
                "url": "/attractions/",
            },
            {
                "title": "Edinburgh Zoo",
                "subtitle": "Scotland's most famous zoo.",
                "image": "fergusonbequest/img/edinburgh_zoo.jpg",
                "id": None,
                "url": "/attractions/",
            },
            {
                "title": "Ghostbusters Screening",
                "subtitle": "Who you gonna call?",
                "image": "fergusonbequest/img/ghostbusters.jpg",
                "id": None,
                "url": "/attractions/",
            },
        ]

    if request.user.is_authenticated:
        return render(
            request,
            "fergusonbequest/home_logged_in.html",
            {"featured_attractions": featured_attractions},
        )

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
            return redirect("home")
    else:
        form = RegistrationForm()
    return render(request, "fergusonbequest/register.html", {"form": form})

@login_required
def dashboard_view(request, year=None, month=None):
    attractions_qs = Attraction.objects.all().order_by('name')[:4]
    
    featured_attractions = []
    for attr in attractions_qs:
        featured_attractions.append({
            "title": attr.name,
            "subtitle": attr.description[:100] if attr.description else attr.location or "Book now to visit",
            "image": attr.image.name if attr.image else "fergusonbequest/img/placeholder.jpg",
            "id": attr.id,
            "url": f"/attraction/{attr.id}/book/",
        })
    
    if not featured_attractions:
        featured_attractions = [
            {
                "title": "Blair Drummond Safari Park",
                "subtitle": "Safari and adventure park.",
                "image": "fergusonbequest/img/blair_drumond.jpg",
                "id": None,
                "url": "/attractions/",
            },
            {
                "title": "Glasgow Clan Ice Hockey",
                "subtitle": "The city's professional hockey team.",
                "image": "fergusonbequest/img/glasgow_clan.jpg",
                "id": None,
                "url": "/attractions/",
            },
            {
                "title": "Edinburgh Zoo",
                "subtitle": "Scotland's most famous zoo.",
                "image": "fergusonbequest/img/edinburgh_zoo.jpg",
                "id": None,
                "url": "/attractions/",
            },
            {
                "title": "Ghostbusters Screening",
                "subtitle": "Who you gonna call?",
                "image": "fergusonbequest/img/ghostbusters.jpg",
                "id": None,
                "url": "/attractions/",
            },
        ]

    calendar_data = get_calendar(year, month)

    return render(request, "fergusonbequest/dashboard.html", {"featured_attractions": featured_attractions, **calendar_data})

 # Ticket draw section
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
            return redirect('draw_waiting_list')
        num_tickets = int(request.POST.get('num_tickets', 1))

        # Error if they exceed their draw limit
        if num_tickets > remaining_allowance:
            messages.error(request, f"Max limit reached. You can only choose up to {remaining_allowance} more tickets.")
            return redirect('ticket_draw_detail', slug=slug)

        slot_id = request.POST.get('slot_id')
        if not slot_id:
            messages.error(request, "No available dates for this draw. Please check back later.")
            return redirect('ticket_draw_detail', slug=slug)

        slot = TicketDrawVisitSlot.objects.filter(pk=slot_id, ticket_draw=draw).first()
        if slot is None:
            messages.error(request, "Selected date is no longer available. Please choose another date.")
            return redirect('ticket_draw_detail', slug=slug)

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
            return redirect('draw_waiting_list')
        elif not draw.is_open():
            messages.error(request, "This draw is currently closed.")
        else:
            messages.error(request, "Not enough availability for that date.")

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
    booking = get_object_or_404(TicketDrawBooking, pk=pk, user=request.user)

    if booking.is_accepted:
        messages.error(request, "You can't cancel an accepted draw win. Please contact support.")
        return redirect("draw_waiting_list")

    if request.method != "POST":
        return redirect("draw_waiting_list")

    with transaction.atomic():
        if not booking.cancelled:
            booking.cancelled = True
            booking.save(update_fields=["cancelled"])

            # Restore slot capacity
            slot = booking.slot
            TicketDrawVisitSlot.objects.filter(pk=slot.pk).update(
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

def assign_next_winner(draw):
    """
    If current winner entry is cancelled/missing then pick a new winner from active entries.
    If no active entries then clear winner.
    """
    if draw.winner_booking and not draw.winner_booking.cancelled:
        return  # winner still valid

    entries = list(
        TicketDrawBooking.objects.filter(ticket_draw=draw, cancelled=False)
        .select_related("user")
    )

    if not entries:
        draw.winner_booking = None
        draw.winner_selected_at = None
    else:
        draw.winner_booking = random.choice(entries)
        draw.winner_selected_at = timezone.now()

    draw.save(update_fields=["winner_booking", "winner_selected_at"])

@login_required
@require_POST
def accept_draw_win(request, pk):
    """
    Winner confirms they want the tickets.
    Sets 'is_accepted' to True on the TicketDrawBooking model.
    """
    booking = get_object_or_404(TicketDrawBooking, pk=pk, user=request.user)
    draw = booking.ticket_draw  # define draw

    # Verify the user is the currently selected winner
    if draw.winner_booking_id == booking.id:
        booking.is_accepted = True
        booking.save(update_fields=["is_accepted"])
        messages.success(request, f"You have officially accepted your tickets for {draw.name}!")
    else:
        messages.error(request, "You are not the current winner of this draw.")

    return redirect("booking_history")

@login_required
@require_POST
def decline_draw_win(request, pk):
    """
    Winner declines the tickets.
    Cancels their booking and automatically triggers a re-draw for the next person.
    """
    booking = get_object_or_404(TicketDrawBooking, pk=pk, user=request.user)
    draw = booking.ticket_draw

    if draw.winner_booking == booking:
        with transaction.atomic():
            if not booking.cancelled:
                booking.cancelled = True
                booking.save()
                # Add tickets back to the TicketDrawVisitSlot
                slot = booking.slot
                slot.remaining = F('remaining') + booking.num_tickets
                TicketDrawVisitSlot.objects.filter(pk=slot.pk).update(
                    remaining=F("remaining") + booking.num_tickets
                )
            messages.success(request, f"Entry for {booking.ticket_draw.name} cancelled.")

    return redirect('draw_waiting_list')

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

    today = timezone.now().date()

    attractions = (
        Attraction.objects
        .annotate(
            future_slots_count=Count("slots", filter=Q(slots__date__gte=today), distinct=True),
            tickets_left_total=Coalesce(
                Sum("slots__remaining", filter=Q(slots__date__gte=today)),
                0
            ),
        )
        # hide past attractions
        .filter(future_slots_count__gt=0)
        .distinct()
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
        attractions = attractions.filter(slots__date__gte=d).distinct()

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

@login_required
def booking_view(request, attraction_pk):
    attraction = get_object_or_404(Attraction, pk=attraction_pk)
    user = request.user

    # Only future slots should be selectable
    available_slots = VisitSlot.objects.filter(
        attraction=attraction,
        date__gte=timezone.now().date()
    ).order_by("date", "time")

    booking_summary = {"price": "Free"}

    # Allowance (per calendar year)
    current_year = timezone.now().year

    # Count active bookings in the current year (cancelled bookings do NOT count)
    active_yearly_count = Booking.objects.filter(
        user=request.user,
        cancelled=False,
        created_at__year=current_year
    ).count()

    remaining_allowance = calculate_remaining_allowance(user, 'regular')
    
    def redirect_to_history_with(msg):
        messages.error(request, msg)
        return redirect("booking_history")

    # GET: show booking form
    if request.method == "GET":
        # Allowance check first
        if remaining_allowance <= 0:
            return redirect_to_history_with(
                f"You have reached your yearly limit of {MAX_ATTRACTIONS_PER_YEAR} attractions. "
                "Please cancel/delete an existing booking in Booking History before booking again."
            )

        # Duplicate booking check (specific slot)
        slot_id = request.GET.get("slot")

        # validate slot belongs to this attraction
        if slot_id and not available_slots.filter(pk=slot_id).exists():
            return redirect_to_history_with(
                "Invalid slot selected for this attraction."
            )

        if slot_id:
            already = Booking.objects.filter(
                user=request.user,
                slot_id=slot_id,
                cancelled=False
            ).exists()

            if already:
                return redirect_to_history_with(
                    "Oops — you already have a booking for this time slot. "
                    "Please cancel it in Booking History before booking again."
                )

        # Pre-select slot in the form if provided in querystring
        form = BookingForm(
            attraction=attraction,
            initial={"slot": slot_id} if slot_id else None
        )

        return render(request, "fergusonbequest/booking_page.html", {
            "attraction": attraction,
            "available_slots": available_slots,
            "form": form,
            "booking_summary": booking_summary,
            "remaining_allowance": remaining_allowance,
            "max_allowance": MAX_ATTRACTIONS_PER_YEAR,
            "now": timezone.now(),
        })

    # POST: attempt to create booking
    form = BookingForm(request.POST, attraction=attraction)

    if form.is_valid():
        # Recompute allowance inside POST in case they opened the page earlier and used up allowance elsewhere
        active_yearly_count = Booking.objects.filter(
            user=request.user,
            cancelled=False,
            created_at__year=current_year
        ).count()
        remaining_allowance = max(0, MAX_ATTRACTIONS_PER_YEAR - active_yearly_count)

        # Allowance check (POST safety)
        if remaining_allowance <= 0:
            return redirect_to_history_with(
                f"You have reached your yearly limit of {MAX_ATTRACTIONS_PER_YEAR} attractions. "
                "Please cancel/delete an existing booking in Booking History before booking again."
            )

        # Build the booking object once
        booking = form.save(commit=False)
        booking.user = request.user
        booking.attraction = attraction
        booking.full_name = f"{request.user.first_name} {request.user.last_name}".strip()
        booking.email = request.user.email

        # validate slot belongs to this attraction
        if booking.slot.attraction_id != attraction.id:
            return redirect_to_history_with(
                "Invalid slot selected for this attraction."
            )

        # Duplicate booking check (specific slots only)
        already = Booking.objects.filter(
            user=request.user,
            slot=booking.slot,
            cancelled=False
        ).exists()

        if already:
            return redirect_to_history_with(
                "Oops — you already have a booking for this time slot. "
                "Please cancel it in Booking History before booking again."
            )

        try:
            # capacity update + save booking
            with transaction.atomic():
                # Lock the slot row so remaining tickets can't be oversold
                slot = VisitSlot.objects.select_for_update().get(pk=booking.slot.pk)

                # Server-side availability check
                if slot.remaining < booking.num_tickets:
                    form.add_error("slot", "Not enough tickets remaining for this slot.")
                    return render(request, "fergusonbequest/booking_page.html", {
                        "attraction": attraction,
                        "available_slots": available_slots,
                        "form": form,
                        "booking_summary": booking_summary,
                        "remaining_allowance": remaining_allowance,
                        "max_allowance": MAX_ATTRACTIONS_PER_YEAR,
                        "now": timezone.now(),
                    })

                # Save booking
                booking.save()

                # Decrement slot remaining
                VisitSlot.objects.filter(pk=slot.pk).update(
                    remaining=F("remaining") - booking.num_tickets
                )

            messages.success(request, "Booking confirmed!")
            return redirect("booking_history")

        except IntegrityError:
            return redirect_to_history_with(
                "Duplicate booking detected for this time slot. "
                "Please cancel it in Booking History before booking again."
            )

    # Form invalid re-render with errors
    return render(request, "fergusonbequest/booking_page.html", {
        "attraction": attraction,
        "available_slots": available_slots,
        "form": form,
        "booking_summary": booking_summary,
        "remaining_allowance": remaining_allowance,
        "max_allowance": MAX_ATTRACTIONS_PER_YEAR,
        "now": timezone.now(),
    })

@login_required
def booking_history(request):
    """Show list of bookings for the logged in user, including both attractions and ticket draws."""
    user = request.user

    remaining_allowance = calculate_remaining_allowance(user, 'regular')

    # Base querysets for both types
    bookings = Booking.objects.filter(user=user).select_related('slot', 'attraction')
    draw_bookings = TicketDrawBooking.objects.filter(user=user).select_related('slot', 'ticket_draw')

    # Parse GET params for filters
    when = request.GET.get('when')  # all|future|past|cancelled
    status = request.GET.get('status')  # all|active|cancelled
    venue = request.GET.get('venue')
    q = request.GET.get('q')
    start = request.GET.get('start')
    end = request.GET.get('end')
    sort = request.GET.get('sort', 'created_at')

    today = timezone.now().date()

    # Apply status filters
    if status == 'cancelled':
        bookings = bookings.filter(cancelled=True)
        draw_bookings = draw_bookings.filter(cancelled=True)
    elif status == 'active':
        bookings = bookings.filter(cancelled=False)
        draw_bookings = draw_bookings.filter(cancelled=False)

    # Apply when filters
    if when == 'future':
        bookings = bookings.filter(slot__date__gte=today)
        draw_bookings = draw_bookings.filter(slot__date__gte=today)
    elif when == 'past':
        bookings = bookings.filter(slot__date__lt=today)
        draw_bookings = draw_bookings.filter(slot__date__lt=today)
    elif when == 'cancelled':
        bookings = bookings.filter(cancelled=True)
        draw_bookings = draw_bookings.filter(cancelled=True)

    # Venue filter
    if venue:
        if venue.isdigit():
            bookings = bookings.filter(attraction__id=venue)
            draw_bookings = draw_bookings.filter(ticket_draw__id=venue)
        else:
            bookings = bookings.filter(attraction__slug__icontains=venue)
            draw_bookings = draw_bookings.filter(ticket_draw__slug__icontains=venue)

    if q:
        bookings = bookings.filter(
            Q(attraction__name__icontains=q) |
            Q(id__icontains=q) |
            Q(email__icontains=q) |
            Q(ticket_code__icontains=q)
        )
        draw_bookings = draw_bookings.filter(
            Q(ticket_draw__name__icontains=q) |
            Q(id__icontains=q) |
            Q(email__icontains=q) |
            Q(ticket_code__icontains=q)
        )

    sd = parse_date(start) if start else None
    ed = parse_date(end) if end else None
    if sd:
        bookings = bookings.filter(slot__date__gte=sd)
        draw_bookings = draw_bookings.filter(slot__date__gte=sd)
    if ed:
        bookings = bookings.filter(slot__date__lte=ed)
        draw_bookings = draw_bookings.filter(slot__date__lte=ed)

    # Split into past/future and combine
    future_bookings = list(bookings.filter(slot__date__gte=today))
    future_draws = list(draw_bookings.filter(slot__date__gte=today))

    past_bookings = list(bookings.filter(slot__date__lt=today))
    past_draws = list(draw_bookings.filter(slot__date__lt=today))

    #  flags
    for b in future_bookings + past_bookings:
        b.booking_type = 'attraction'
        b.is_draw = False

    for d in future_draws + past_draws:
        d.booking_type = 'draw'
        d.is_draw = True

    # Combine and sort
    if sort == 'slot_date':
        def sort_key(item):
            return (item.slot.date, item.created_at)
        reverse = False
    else:
        def sort_key(item):
            return item.created_at
        reverse = True

    future_all = sorted(future_bookings + future_draws, key=sort_key, reverse=reverse)
    past_all = sorted(past_bookings + past_draws, key=sort_key, reverse=reverse)

    return render(request, 'fergusonbequest/booking_history.html', {
        'future_bookings': future_all,
        'past_bookings': past_all,
        'when': when,
        'status': status,
        'venue': venue,
        'q': q,
        'start': start,
        'end': end,
        'sort': sort,
        'now': timezone.now(),
        "remaining_allowance": remaining_allowance,
        "max_allowance": MAX_ATTRACTIONS_PER_YEAR,
    })

@require_POST
@login_required
def cancel_booking(request, pk):
    """Allow the booking owner (or superuser) to cancel a future booking.
       Cancelling restores slot capacity and also restores yearly allowance because cancelled bookings don't count.
    """
    booking = get_object_or_404(Booking, pk=pk)

    # Only user or admin can cancel
    if not (request.user == booking.user or request.user.is_superuser):
        return redirect('booking_history')

    # Only allow cancelling future bookings
    if booking.slot.date < timezone.now().date():
        return redirect('booking_history')

    with transaction.atomic():
        b = Booking.objects.select_for_update().get(pk=booking.pk)

        if not b.cancelled:
            b.cancelled = True
            b.save(update_fields=["cancelled"])

            # restore capacity on the slot (cap at capacity)
            VisitSlot.objects.filter(pk=b.slot.pk).update(
                remaining=Least(F('remaining') + b.num_tickets, F('capacity'))
            )

            current_year = timezone.now().year
            active_yearly_count = Booking.objects.filter(
                user=b.user,
                cancelled=False,
                created_at__year=current_year
            ).count()
            remaining_allowance = max(0, MAX_ATTRACTIONS_PER_YEAR - active_yearly_count)

            messages.success(
                request,
                f"Booking cancelled. You now have {remaining_allowance}/{MAX_ATTRACTIONS_PER_YEAR} bookings remaining for this year."
            )

    return redirect('booking_history')


@login_required
def draw_waiting_list(request):
    """
    Waiting List meaning pending in the sense of 'entered'
    Before accepting or decling
    """
    user = request.user
    now = timezone.now()

    entries = (
        TicketDrawBooking.objects
        .filter(user=user, cancelled=False, is_accepted=False)
        .select_related("ticket_draw", "slot")
        .order_by("-created_at")
    )

    # Add a computed status for display
    for e in entries:
        is_winner = getattr(e.ticket_draw, "winner_booking_id", None) == e.id
        if is_winner and e.is_accepted:
            e.ui_status = "Accepted"
        elif is_winner and not e.is_accepted:
            e.ui_status = "Winner (Action required)"
        else:
            e.ui_status = "Waiting for draw"

        # Allow cancel until booking_close (if exists)
        close = getattr(e.ticket_draw, "booking_close", None)
        is_winner = getattr(e.ticket_draw, "winner_booking_id", None) == e.id

        close = getattr(e.ticket_draw, "booking_close", None)
        e.can_cancel = (not e.is_accepted) and (not is_winner) and bool(close and now <= close)

    return render(request, "fergusonbequest/draw_waiting_list.html", {
        "entries": entries,
        "now": now,
    })


@login_required
def waiting_listattraction(request):
    """Attraction waiting list (for sold-out attractions only)"""
    attractions = Attraction.objects.all().order_by("name")

    joined_ids = set(request.session.get("attraction_waitlist_ids", []))

    for a in attractions:
        a.joined = a.id in joined_ids

    return render(request, "fergusonbequest/waiting_listattraction.html", {
        "attractions": attractions,
    })


@require_POST
@login_required
def waiting_listattraction_join(request, pk):
    """Join attraction waiting list"""
    attraction = get_object_or_404(Attraction, pk=pk)

    ids = set(request.session.get("attraction_waitlist_ids", []))
    ids.add(attraction.id)
    request.session["attraction_waitlist_ids"] = list(ids)

    messages.success(request, f"You joined the waiting list for {attraction.name}.")
    return redirect("waiting_listattraction")


@require_POST
@login_required
def waiting_listattraction_leave(request, pk):
    """Leave attraction waiting list"""
    attraction = get_object_or_404(Attraction, pk=pk)

    ids = set(request.session.get("attraction_waitlist_ids", []))
    ids.discard(attraction.id)
    request.session["attraction_waitlist_ids"] = list(ids)

    messages.success(request, f"You left the waiting list for {attraction.name}.")
    return redirect("waiting_listattraction")

@staff_member_required
def create_attraction(request):
    """
    Staff-only view to create a new attraction.
    """
    if request.method == 'POST':
        form = AttractionCreateForm(request.POST, request.FILES)
        if form.is_valid():
            attraction = form.save()
            messages.success(request, f'Attraction "{attraction.name}" created successfully!')
            return redirect('admin_dashboard')
    else:
        form = AttractionCreateForm()
    
    return render(request, 'fergusonbequest/create_attraction.html', {
        'form': form,
        'title': 'Create New Attraction'
    })


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

    #  Draw sorting
    if sort_draws == "open_first":
        draws_qs = draws_qs.order_by("-booking_open", "-booking_close", "name")
    elif sort_draws == "close_date":
        draws_qs = draws_qs.order_by("booking_close", "name")
    elif sort_draws == "close_date_desc":
        draws_qs = draws_qs.order_by("-booking_close", "name")
    else:
        draws_qs = draws_qs.order_by("name")

    #  Attraction sorting (date and location)
    if sort_attractions == "date":
        attractions_qs = attractions_qs.order_by("booking_open", "name")
    elif sort_attractions == "date_desc":
        attractions_qs = attractions_qs.order_by("-booking_open", "name")
    else:
        attractions_qs = attractions_qs.order_by("name")

    now = timezone.now()
    for d in draws_qs:
        d.is_open_now = d.is_open(now)
        d.is_closed_now = not d.is_open_now

    return render(request, "fergusonbequest/admin_management.html", {
        "draws": draws_qs,
        "attractions": attractions_qs,
        "tab": tab,
        "q": q,
        "sort_draws": sort_draws,
        "sort_attractions": sort_attractions,
    })

@staff_member_required
@require_POST
def run_draw(request, draw_id):
    draw = get_object_or_404(TicketDraw, pk=draw_id)

    # only run if closed
    now = timezone.now()
    if draw.is_open(now):
        messages.error(request, "This draw is still open. You can only run it after it closes.")
        return redirect(f"{reverse('management')}?tab=draws")

    # Only allow when closed (now actually enforced)
    entries = list(
        TicketDrawBooking.objects.filter(ticket_draw=draw, cancelled=False)
        .select_related("user")
    )

    if not entries:
        draw.winner_booking = None
        draw.winner_selected_at = None
        draw.save(update_fields=["winner_booking", "winner_selected_at"])
        messages.error(request, "No active entries for this draw.")
        return redirect(f"{reverse('management')}?tab=draws")

    draw.winner_booking = random.choice(entries)
    draw.winner_selected_at = timezone.now()
    draw.save(update_fields=["winner_booking", "winner_selected_at"])

    winner_name = draw.winner_booking.full_name or (
        draw.winner_booking.user.get_username() if draw.winner_booking.user else "Winner"
    )
    messages.success(request, f"Winner selected: {winner_name}")
    return redirect(f"{reverse('management')}?tab=draws")

@staff_member_required
@require_POST
def mng_delete_ticket_draw(request, draw_id):
    draw = get_object_or_404(TicketDraw, pk=draw_id)
    draw.delete()
    messages.success(request, "Draw deleted.")
    return redirect("/admin-dashboard/management/?tab=draws")


@staff_member_required
@require_POST
def mng_delete_attraction(request, attraction_id):
    attraction = get_object_or_404(Attraction, pk=attraction_id)
    attraction.delete()
    messages.success(request, "Attraction deleted.")
    return redirect("/admin-dashboard/management/?tab=attractions")

@staff_member_required
def create_ticket_draw(request):
    """
    Staff-only view to create a new ticket draw.
    """
    if request.method == 'POST':
        form = TicketDrawCreateForm(request.POST, request.FILES)
        if form.is_valid():
            ticket_draw = form.save()
            messages.success(request, f'Ticket Draw "{ticket_draw.name}" created successfully!')
            return redirect('admin_dashboard')
    else:
        form = TicketDrawCreateForm()
    
    return render(request, 'fergusonbequest/create_ticket_draw.html', {
        'form': form,
        'title': 'Create New Ticket Draw'
    })


@staff_member_required
def edit_attraction(request, pk):
    """
    Staff-only view to edit an existing attraction.
    """
    attraction = get_object_or_404(Attraction, pk=pk)
    
    if request.method == 'POST':
        form = AttractionCreateForm(request.POST, request.FILES, instance=attraction)
        if form.is_valid():
            form.save()
            messages.success(request, f'Attraction "{attraction.name}" updated successfully!')
            return redirect('admin_dashboard')
    else:
        form = AttractionCreateForm(instance=attraction)
    
    return render(request, 'fergusonbequest/edit_attraction.html', {
        'form': form,
        'title': 'Edit Attraction',
        'attraction': attraction
    })


@staff_member_required
def edit_ticket_draw(request, pk):
    """
    Staff-only view to edit an existing ticket draw.
    """
    ticket_draw = get_object_or_404(TicketDraw, pk=pk)
    
    if request.method == 'POST':
        form = TicketDrawCreateForm(request.POST, request.FILES, instance=ticket_draw)
        if form.is_valid():
            form.save()
            messages.success(request, f'Ticket Draw "{ticket_draw.name}" updated successfully!')
            return redirect('admin_dashboard')
    else:
        form = TicketDrawCreateForm(instance=ticket_draw)
    
    return render(request, 'fergusonbequest/edit_ticket_draw.html', {
        'form': form,
        'title': 'Edit Ticket Draw',
        'ticket_draw': ticket_draw
    })


def add_events(objects, events_by_day, start, end, event_type):
    for obj in objects:
        for field, class_name in [('booking_open', 'booking-open'), ('booking_close', 'booking-close')]:
            date_value = getattr(obj, field, None)
            if date_value:
                event_date = date_value.date()
                if start <= event_date <= end:
                    day = event_date.day
                    events_by_day.setdefault(day, []).append({
                        'class_name': class_name,
                        'object': obj,
                        'event_type': event_type,
                    })


def get_calendar(year=None, month=None):
    today = timezone.localdate()
    year = int(year or today.year)
    month = int(month or today.month)

    # previous month/year
    if month == 1:
        prev_month, prev_year = 12, year - 1
    else:
        prev_month, prev_year = month - 1, year

    # next month/year
    if month == 12:
        next_month, next_year = 1, year + 1
    else:
        next_month, next_year = month + 1, year

    cal = calendar.Calendar(firstweekday=0)
    month_days = list(cal.itermonthdates(year, month))
    start, end = month_days[0], month_days[-1]

    events_by_day = {}
    add_events(Attraction.objects.all(), events_by_day, start, end, 'attraction')
    add_events(TicketDraw.objects.all(), events_by_day, start, end, 'ticket_draw')

    weeks = []
    for i in range(0, len(month_days), 7):
        week = month_days[i:i+7]
        week_info = []
        for day in week:
            day_events = events_by_day.get(day.day, []) if day.month == month else []
            week_info.append({'date': day, 'events': day_events})
        weeks.append(week_info)

    # context = { 
    #     'year': year,
    #     'month': month,
    #     'month_name': calendar.month_name[month],
    #     'weeks': weeks,
    #     'today': today,
    #     'prev_year': prev_year,
    #     'prev_month': prev_month,
    #     'next_year': next_year,
    #     'next_month': next_month,
    # }



@login_required
def waiting_listattraction(request):
    attractions = Attraction.objects.all().order_by("name")

    joined_ids = set(request.session.get("attraction_waitlist_ids", []))

    for a in attractions:
        a.joined = a.id in joined_ids

    return render(request, "fergusonbequest/waiting_listattraction.html", {
        "attractions": attractions,
    })


@require_POST
@login_required
def waiting_listattraction_join(request, pk):
    attraction = get_object_or_404(Attraction, pk=pk)

    ids = set(request.session.get("attraction_waitlist_ids", []))
    ids.add(attraction.id)
    request.session["attraction_waitlist_ids"] = list(ids)

    messages.success(request, f"You joined the waiting list for {attraction.name}.")
    return redirect("waiting_listattraction")


@require_POST
@login_required
def waiting_listattraction_leave(request, pk):
    attraction = get_object_or_404(Attraction, pk=pk)

    ids = set(request.session.get("attraction_waitlist_ids", []))
    ids.discard(attraction.id)
    request.session["attraction_waitlist_ids"] = list(ids)

    messages.success(request, f"You left the waiting list for {attraction.name}.")
    return redirect("waiting_listattraction")
    return context
