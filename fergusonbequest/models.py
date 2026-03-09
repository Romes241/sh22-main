from django.db import models
from django.utils import timezone
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Q
from django.db import IntegrityError

# Create your models here.
YEAR_LIMIT_DEFAULT = 3

ATTRACTION_TYPE_CHOICES = [
    ('regular', 'Regular Attraction'),
    ('weekly_event', 'Weekly Ticket Event'),
]

"""
Representing an attraction 
Each attraction can have multiple visit slots and bookings.
"""
class Attraction(models.Model):
    name = models.CharField(max_length=120)
    # short URL-safe identifier (e.g. "edinburgh-zoo")
    # used for building URLs like /attractions/edinburgh-zoo/
    slug = models.SlugField(unique=True)
    # location of attraction
    location = models.CharField(max_length=120, blank=True)
    # image related to the attraction
    image = models.ImageField(upload_to='images/', blank=True, null=True)
    # short summary or description displayed on the detail page
    description = models.TextField(blank=True)
    # contact info for users to reach the attraction admin
    contact_email = models.EmailField(blank=True)
    # any special Terms & Conditions specific to this attraction
    # displayed in the booking form before confirming
    terms = models.TextField(blank=True)
    # when bookings open — before this date users can’t book
    booking_open = models.DateTimeField(null=True, blank=True)
    # when bookings close — after this date users can’t book
    booking_close = models.DateTimeField(null=True, blank=True)
    # how many times a user can book this attraction per year
    # default value is the constant defined above
    per_year_limit = models.PositiveIntegerField(default=YEAR_LIMIT_DEFAULT)
    # type of attraction: regular or weekly event
    attraction_type = models.CharField(
        max_length=20,
        choices=ATTRACTION_TYPE_CHOICES,
        default='regular'
    )
    # time that attraction would take
    duration_minutes = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return self.name

    def is_open(self, dt=None):
        """
        Helper method to check if this attraction is currently bookable.
        Returns True only if:
          - booking_open is None or has passed
          - AND booking_close is None or not yet reached
        """
        dt = dt or timezone.now()

        ok_open = (self.booking_open is None) or (dt >= self.booking_open)
        ok_close = (self.booking_close is None) or (dt <= self.booking_close)

        return ok_open and ok_close

    @property
    def remaining_total(self):
        """
        Calculates how many total tickets/codes remain across all VisitSlots.
        Uses a reverse lookup:
            self.slots -> all VisitSlot objects linked to this attraction.
        """
        return sum(s.remaining for s in self.slots.all())

    cancel_deadline = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Users can cancel their booking until this date/time. Leave empty for 'no cancellation allowed'."
    )

    def can_cancel_booking(self):
        if not self.cancel_deadline:
            return False
        return timezone.now() <= self.cancel_deadline

class TicketDraw(models.Model):
    name = models.CharField(max_length=120)
    # short URL-safe identifier (e.g. "edinburgh-zoo")
    # used for building URLs like /attractions/edinburgh-zoo/
    slug = models.SlugField(unique=True)
    # location of attraction
    location = models.CharField(max_length=120, blank=True)
    # image related to the attraction
    image = models.ImageField(upload_to='images/', blank=True, null=True)
    # short summary or description displayed on the detail page
    description = models.TextField(blank=True)
    # contact info for users to reach the attraction admin
    contact_email = models.EmailField(blank=True)
    # any special Terms & Conditions specific to this attraction
    # displayed in the booking form before confirming
    terms = models.TextField(blank=True)
    # when bookings open — before this date users can’t book
    booking_open = models.DateTimeField(null=True, blank=True)
    # when bookings close — after this date users can’t book
    booking_close = models.DateTimeField(null=True, blank=True)
    # how many times a user can book this attraction per year
    # default value is the constant defined above
    # date of the draw
    draw_date = models.DateTimeField()
    per_year_limit = models.PositiveIntegerField(default=YEAR_LIMIT_DEFAULT)
    winner_booking = models.ForeignKey(
        "TicketDrawBooking",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="won_for_draw"
    )
    winner_selected_at = models.DateTimeField(null=True, blank=True)
    # type of attraction: regular or weekly event
    attraction_type = models.CharField(
        max_length=20,
        choices=ATTRACTION_TYPE_CHOICES,
        default='weekly_event'
    )

    def __str__(self):
        return self.name

    def is_open(self, dt=None):
        """
        Helper method to check if this attraction is currently bookable.
        Returns True only if:
          - booking_open is None or has passed
          - AND booking_close is None or not yet reached
        """
        dt = dt or timezone.now()

        ok_open = (self.booking_open is None) or (dt >= self.booking_open)
        ok_close = (self.booking_close is None) or (dt <= self.booking_close)

        return ok_open and ok_close

    @property
    def remaining_total(self):
        """
        Calculates how many total tickets/codes remain across all VisitSlots.
        Uses a reverse lookup:
            self.slots -> all VisitSlot objects linked to this attraction.
        """
        return sum(s.remaining for s in self.slots.all())

class VisitSlot(models.Model):
    """A dated (optionally timed) bookable slot with capacity control."""
    attraction = models.ForeignKey('Attraction', related_name='slots', on_delete=models.CASCADE)
    date = models.DateField()
    time = models.TimeField(blank=True, null=True)
    capacity = models.PositiveIntegerField(default=20)
    remaining = models.PositiveIntegerField(default=20)

    class Meta:
        ordering = ('date', 'time')

    def __str__(self):
        t = self.time.strftime("%H:%M") if self.time else "Any time"
        return f"{self.attraction.name} – {self.date} {t}"

class TicketDrawVisitSlot(models.Model):
    """A dated (optionally timed) bookable slot with capacity control."""
    ticket_draw = models.ForeignKey('TicketDraw', related_name='slots', on_delete=models.CASCADE)
    date = models.DateField()
    time = models.TimeField(blank=True, null=True)
    capacity = models.PositiveIntegerField(default=20)
    remaining = models.PositiveIntegerField(default=20)

    class Meta:
        ordering = ('date', 'time')

    def __str__(self):
        t = self.time.strftime("%H:%M") if self.time else "Any time"
        return f"{self.ticket_draw.name} – {self.date} {t}"


class Booking(models.Model):
    attraction = models.ForeignKey("Attraction", on_delete=models.CASCADE)
    slot = models.ForeignKey("VisitSlot", on_delete=models.PROTECT)

    # Data for history
    full_name = models.CharField(max_length=120)
    email = models.EmailField()

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bookings"
    )

    num_tickets = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(2)]
    )

    agreed_terms = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    cancelled = models.BooleanField(default=False)
    ticket_code = models.CharField(max_length=100, blank=True, null=True)
    TICKET_TYPE_CHOICES = [
        ("codes", "E-ticket codes"),
        ("pdf_template", "PDF template"),
        ("pdf_template_random", "PDF template + random code"),
        ("pdf_individual", "Individual PDF tickets"),
        ("qr_individual", "Individual QR tickets"),
        ("booking_code", "Generic booking code"),
        ("instructions", "Staff-card instructions"),
        ("box_office", "Box office collection"),
    ]
    ticket_type = models.CharField(max_length=50,choices=TICKET_TYPE_CHOICES,blank=True,null=True)
    ticket_file = models.FileField(upload_to="tickets/", blank=True, null=True)
    ticket_sent = models.BooleanField(default=False)
    ticket_sent_at = models.DateTimeField(null=True, blank=True)
    ticket_instructions = models.TextField(blank=True, null=True)
    generic_booking_code = models.CharField(max_length=100, blank=True, null=True)
    ticket_qr_value = models.TextField(blank=True, null=True)
    ticket_visible_at = models.DateTimeField(null=True, blank=True)

    # when tickets become visible to the user (days before visit date)
    ticket_release_days = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(0), MaxValueValidator(30)],
        help_text="How many days before the visit date the ticket becomes visible to the user."
    )
    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["user", "slot"],
                condition=Q(cancelled=False),
                name="unique_active_booking_per_slot_per_user",
            )
        ]

    def __str__(self):
        return f"{self.user.username} → {self.attraction.name} @ {self.slot}"

    @property
    def year(self):
        return self.created_at.year

    def save(self, *args, **kwargs):
        # Only auto-generate code for random template type
        if self.ticket_type == "pdf_template_random" and not self.ticket_code:
            import uuid
            base = "FB-" + uuid.uuid4().hex[:8].upper()
            tries = 0
            while tries < 5:
                if not Booking.objects.filter(ticket_code=base).exists():
                    self.ticket_code = base
                    break
                base = "FB-" + uuid.uuid4().hex[:8].upper()
                tries += 1
        super().save(*args, **kwargs)

class TicketDrawBooking(models.Model):
    """One reservation for a ticket draw."""
    ticket_draw = models.ForeignKey('TicketDraw', on_delete=models.CASCADE)
    slot = models.ForeignKey(TicketDrawVisitSlot, on_delete=models.PROTECT)
    full_name = models.CharField(max_length=120)
    email = models.EmailField()
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                             blank=True, related_name='ticket_draw_bookings')
    num_tickets = models.PositiveIntegerField(default=1)
    agreed_terms = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    cancelled = models.BooleanField(default=False)
    is_accepted = models.BooleanField(default=False)
    ticket_code = models.CharField(max_length=100, blank=True, null=True)
    TICKET_TYPE_CHOICES = [
        ("codes", "E-ticket codes"),
        ("pdf_template", "PDF template"),
        ("pdf_template_random", "PDF template + random code"),
        ("pdf_individual", "Individual PDF tickets"),
        ("qr_individual", "Individual QR tickets"),
        ("booking_code", "Generic booking code"),
        ("instructions", "Staff-card instructions"),
        ("box_office", "Box office collection"),
    ]
    ticket_type = models.CharField(max_length=50,choices=TICKET_TYPE_CHOICES,blank=True,null=True)
    ticket_file = models.FileField(upload_to="tickets/", blank=True, null=True)
    ticket_sent = models.BooleanField(default=False)
    ticket_sent_at = models.DateTimeField(null=True, blank=True)
    ticket_instructions = models.TextField(blank=True, null=True)
    generic_booking_code = models.CharField(max_length=100, blank=True, null=True)
    ticket_qr_value = models.TextField(blank=True, null=True)
    ticket_visible_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        who = self.user.username if self.user else self.full_name
        return f"{who} → {self.ticket_draw.name} @ {self.slot}"

    @property
    def year(self):
        return self.created_at.year

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

class Profile(models.Model):
    """User profile to extend default User model."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    staff_guid = models.CharField(max_length=64, unique=True, blank=True, null=True) # Placeholder for staff GUID
    eligible= models.BooleanField(default=False) # Placeholder for eligibility status
    eligibility_reason = models.TextField(blank=True, null=True) # Placeholder for eligibility reason
    department = models.CharField(max_length=255, blank=True, null=True) # Placeholder for department field

    def __str__(self):
        return f"Profile of {self.user.username}"
    
class AttractionSuggestion(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    why_recommended = models.TextField(blank=True)

    website_url = models.URLField(blank=True)
    location = models.CharField(max_length=200, blank=True)

    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="attraction_suggestions"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    STATUS_PENDING = "pending"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_IMPLEMENTED = "implemented"
    STATUS_REJECTED = "rejected"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_IN_PROGRESS, "In progress"),
        (STATUS_IMPLEMENTED, "Implemented"),
        (STATUS_REJECTED, "Rejected"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)

    def __str__(self):
        return f"{self.name} ({self.status})"

