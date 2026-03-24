from django.db import models
from django.utils import timezone
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Q
from django.db import IntegrityError
import uuid

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

    # winner info (for run draw results)
    winner_booking = models.ForeignKey(
        "TicketDrawBooking",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="won_for_draw"
    )
    winner_selected_at = models.DateTimeField(null=True, blank=True)

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

    cancel_deadline = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Users can cancel their booking until this date/time. Leave empty for 'no cancellation allowed'."
    )

    def can_cancel_booking(self):
        if not self.cancel_deadline:
            return False
        return timezone.now() <= self.cancel_deadline

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
    ticket_type = models.CharField(max_length=50, choices=TICKET_TYPE_CHOICES, blank=True, null=True)

    feedback_email_sent = models.BooleanField(default=False)
    feedback_email_sent_at = models.DateTimeField(null=True, blank=True)
    feedback_reminder_sent = models.BooleanField(default=False)
    feedback_reminder_sent_at = models.DateTimeField(null=True, blank=True)
    ticket_sent = models.BooleanField(default=False)
    ticket_sent_at = models.DateTimeField(null=True, blank=True)
    ticket_instructions = models.TextField(blank=True, null=True)
    generic_booking_code = models.CharField(max_length=100, blank=True, null=True)
    ticket_qr_value = models.TextField(blank=True, null=True)
    ticket_visible_at = models.DateTimeField(null=True, blank=True)
    box_office_notes = models.TextField(blank=True, null=True)

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
        if self.ticket_type == "pdf_template_random" and not self.ticket_code:
            base = "FB-" + uuid.uuid4().hex[:8].upper()
            tries = 0

            while tries < 5:
                if not Booking.objects.filter(ticket_code=base).exists():
                    self.ticket_code = base
                    break
                base = "FB-" + uuid.uuid4().hex[:8].upper()
                tries += 1

        super().save(*args, **kwargs)

    @property
    def uploaded_ticket_count(self):
        return self.tickets.count()

    @property
    def needs_more_tickets(self):
        return self.uploaded_ticket_count < self.num_tickets


class BookingFeedback(models.Model):
    booking = models.OneToOneField(
        "Booking",
        on_delete=models.CASCADE,
        related_name="feedback_submission",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="booking_feedback_submissions",
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comments = models.TextField(blank=True)
    staff_full_name = models.CharField(max_length=150)
    staff_email = models.EmailField()
    staff_guid = models.CharField(max_length=64, blank=True)
    staff_department = models.CharField(max_length=255, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-submitted_at",)

    def __str__(self):
        return f"Feedback for booking #{self.booking_id}"

class BookingTicket(models.Model):
    booking = models.ForeignKey(
        Booking,
        related_name="tickets",
        on_delete=models.CASCADE
    )
    file = models.FileField(upload_to="tickets/")
    qr_value = models.TextField(blank=True, null=True)
    ticket_code = models.TextField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("sort_order", "id")

    def __str__(self):
        return f"Booking #{self.booking_id} Ticket #{self.id}"

class TicketDrawBooking(models.Model):
    """A draw entry / winner record. Real tickets live on Booking."""
    ticket_draw = models.ForeignKey('TicketDraw', on_delete=models.CASCADE)
    slot = models.ForeignKey(TicketDrawVisitSlot, on_delete=models.PROTECT)
    full_name = models.CharField(max_length=120)
    email = models.EmailField()
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ticket_draw_bookings',
    )
    num_tickets = models.PositiveIntegerField(default=1)
    agreed_terms = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    cancelled = models.BooleanField(default=False)

    # draw state only
    is_accepted = models.BooleanField(default=False)

    # once accepted, create a normal Booking and store it here
    converted_booking = models.OneToOneField(
        'Booking',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='source_draw_booking',
    )

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        who = self.user.username if self.user else self.full_name
        return f"{who} → {self.ticket_draw.name} @ {self.slot}"

    @property
    def year(self):
        return self.created_at.year

class Profile(models.Model):
    """User profile to extend default User model."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    staff_guid = models.CharField(max_length=64, unique=True, blank=True, null=True)  # Placeholder for staff GUID
    eligible = models.BooleanField(default=False)  # Placeholder for eligibility status
    eligibility_reason = models.TextField(blank=True, null=True)  # Placeholder for eligibility reason
    department = models.CharField(max_length=255, blank=True, null=True)  # Placeholder for department field

    def __str__(self):
        return f"Profile of {self.user.username}"


class DiscountCode(models.Model):
    title = models.CharField(max_length=120)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)

    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.code} - {self.title}"


class AttractionSuggestion(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    why_recommended = models.TextField(blank=True)

    website_url = models.URLField(blank=True)
    location = models.CharField(max_length=200, blank=True)

    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="attraction_suggestions",
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

class EmailTemplate(models.Model):
    TYPE_CHOICES = [
        # Confirmation
        ("attraction_confirmation", "Attraction Confirmation"),
        ("draw_confirmation", "Ticket Draw Confirmation"),

        # Cancellation
        ("attraction_cancellation", "Attraction Cancellation"),
        ("draw_cancellation", "Ticket Draw Cancellation"),

        # Ticket Distribution - Send ticket 3 days before if not cancelled, cannot be cancelled after ticket has been sent
        ("attraction_distribution", "Attraction Ticket Distribution"),
        ("draw_distribution", "Ticket Draw Ticket Distribution"),

        # Draw Winner, accept or reject (cant reject after accepting, reject after 72h)
        ("draw_winner", "Ticket Draw Winner"),

        # Attraction Waiting List reallocation (Attraciton Waiting List)
        ("attraction_reallocation", "Attraction Reallocation (Next in waiting list)"),

        # Draw Waiting List Winner - Redraw Winner, Accept or Reject (Waiting List redraw if winner cancelled)
        ("draw_reallocation", "Ticket Draw Reallocation (Redraw Winner)"),

        # Reminder 1 day before of attraction or draw
        ("attraction_reminder", "Attraction Reminder"),
        ("draw_reminder", "Ticket Draw Reminder"),

        # Forms - Feedback
        ("feedback", "Feedback"),

        # Announcements
        ("announcement", "Announcements"),

        # Custom
        ("custom", "Custom"),


    ]

    type = models.CharField(max_length=100, choices=TYPE_CHOICES, default="confirmation")
    name = models.CharField(max_length=100)
    subject = models.CharField(max_length=250)
    body = models.TextField()
    is_default = models.BooleanField(default=False, help_text="Use this as the default template for this email type")

    class Meta:
        # Ensure only one default per type
        constraints = [
            models.UniqueConstraint(
                fields=['type'],
                condition=Q(is_default=True),
                name='unique_default_per_type'
            )
        ]

    def __str__(self):
        return f"{self.get_type_display()} – {self.name}"

class AttractionWaitlistEntry(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="attraction_waitlist_entries",
    )

    attraction = models.ForeignKey(
        "Attraction",
        on_delete=models.CASCADE,
        related_name="waitlist_entries",
    )

    slot = models.ForeignKey(
        "VisitSlot",
        on_delete=models.CASCADE,
        related_name="waitlist_entries",
        null=True,
        blank=True,
    )

    num_tickets = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(2)]
    )

    created_at = models.DateTimeField(auto_now_add=True)
    cancelled = models.BooleanField(default=False)
    notified = models.BooleanField(default=False)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["user", "slot"],
                condition=Q(cancelled=False),
                name="unique_active_slot_waitlist",
            )
        ]

    def __str__(self):
        return f"{self.user.username} → {self.attraction.name} waitlist ({self.num_tickets})"

class TermsAndConditions(models.Model):
    """Singleton model to store editable Terms & Conditions content."""
    
    eligibility = models.TextField(
        default="Attraction and Ticket Draws are available to any member of staff of the University holding a contract of employment with the University. This does not include registered honorary staff, affiliates, or individuals employed directly by other organisations but paid via the University payroll."
    )
    application_limits = models.TextField(
        default="Staff may apply, per calendar year, for a pair of ticket codes for a maximum of 3 Attractions.\n\nStaff may apply for a pair of tickets to each of the Weekly Events (Basketball, Ice Hockey, The Stand) per season.\n\nStaff may enter as many Ticket Draws as they wish and can win 1 per calendar year. Winners will be removed from future draws."
    )
    how_to_book = models.TextField(
        default="Bookings are made via the Ferguson Bequest link within MyGlasgow for Staff. Each individual attraction contains information on how to book. You must select the correct number of tickets required."
    )
    attendance = models.TextField(
        default="Please only apply if you can attend an event or attraction! Your tickets can not necessarily be cancelled and reallocated.\n\nIf, due to unforeseen circumstances, you are unable to attend a pre-booked event or attraction, you may not request further tickets within the same calendar year. Expiry dates cannot be extended and you may not request further tickets within the same calendar year if you do not use your tickets by the expiry date."
    )
    conduct = models.TextField(
        default="During visits, staff should be mindful that they are representing the University of Glasgow and ensure they, and members of their party, conduct themselves in a manner appropriate to the University and its values. Tickets are non-transferable and should not be passed to another person or another staff member. It is your responsibility to ensure the event is suitable for all members of your party."
    )
    liability_and_entry = models.TextField(
        default="The University is in no way liable or responsible for other costs incurred during visits, nor event cancellations or closures. Staff are required to present their staff card and any tickets or confirmations on the day. Staff are subject to venue policies, procedures and safety measures. Tickets are equivalent to event entry on the date advertised and cannot be used as a substitution for monetary value towards goods and/or services."
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Terms and Conditions"

    def __str__(self):
        return "Terms and Conditions"

    @classmethod
    def get(cls):
        """Return the singleton instance."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class MainPageContent(models.Model):
    """Singleton model for editable authenticated main-page content blocks."""

    left_intro = models.TextField(
        default=(
            "The Ferguson Bequest gives University of Glasgow staff exclusive "
            "access to attractions and event ticket draws throughout the year."
        )
    )
    left_bullet_1 = models.CharField(max_length=255, default="Apply for up to three attractions per calendar year")
    left_bullet_2 = models.CharField(max_length=255, default="Enter multiple ticket draws and win once per year")
    left_bullet_3 = models.CharField(max_length=255, default="View all your bookings in Booking History")
    left_warning_title = models.CharField(max_length=200, default="Please apply carefully")
    left_warning_body = models.TextField(default="bookings can’t be cancelled once submitted.")
    left_eligibility_text = models.TextField(
        default="Eligible for University of Glasgow staff with an active contract of employment. Honorary, affiliate, and casual staff are not eligible."
    )

    about_heading = models.CharField(max_length=200, default="About the Ferguson Bequest")
    about_paragraph_1 = models.TextField(
        default=(
            "Professor in Public Health and President of the University Athletics Football Club, "
            "Professor Thomas Ferguson authored classic studies on the origin of Scotland’s social "
            "and health services. In 1977 he bequeathed his estate to the University, with the "
            "instruction that the money be used to foster the social side of University life for "
            "its (then) 2,100 staff."
        )
    )
    about_paragraph_2 = models.TextField(
        default=(
            "The University Court established a committee (the Ferguson Bequest Committee) to "
            "administer the funds. Various corporate memberships and theatre ticket draws are "
            "administered by the Court Office on behalf of the Ferguson Bequest Committee."
        )
    )
    about_image = models.ImageField(upload_to="images/", blank=True, null=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Main Page Content"

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

class FeedbackEmailTemplate(models.Model):
    """Stores the email template for feedback requests. Only one instance should exist."""

    FEEDBACK_MODE_INTERNAL = "internal"
    FEEDBACK_MODE_EXTERNAL = "external"
    FEEDBACK_MODE_CHOICES = [
        (FEEDBACK_MODE_INTERNAL, "Built-in feedback form"),
        (FEEDBACK_MODE_EXTERNAL, "External Microsoft Forms link"),
    ]
    
    subject = models.CharField(
        max_length=200,
        default="How was your visit to {attraction_name}?",
        help_text="Email subject. Use {attraction_name} as placeholder for the attraction name."
    )
    
    body = models.TextField(
        default="""Dear {user_name},

Thank you for using the Ferguson Bequest to visit {attraction_name} on {visit_date}.

We hope you enjoyed your experience! We'd love to hear your feedback to help us improve the Ferguson Bequest service.

Please take a few moments to complete our feedback form:
{feedback_url}

Your feedback is valuable and helps us provide better experiences for all University of Glasgow staff.

Best regards,
The Ferguson Bequest Team

---
This is an automated email. For queries, contact fergusonbequest@glasgow.ac.uk""",
        help_text="Email body. Available placeholders: {user_name}, {attraction_name}, {visit_date}, {feedback_url}"
    )
    
    feedback_url = models.URLField(
        max_length=500,
        blank=True,
        default="",
        help_text="Microsoft Forms feedback URL. Create your form in Microsoft Forms and paste the link here. This field is required to send feedback emails."
    )
    
    enabled = models.BooleanField(
        default=True,
        help_text="Uncheck to disable automatic feedback emails"
    )

    feedback_mode = models.CharField(
        max_length=20,
        choices=FEEDBACK_MODE_CHOICES,
        default=FEEDBACK_MODE_INTERNAL,
        help_text="Choose whether emails link to the in-app feedback form or an external Microsoft Forms URL."
    )

    expiry_days = models.PositiveSmallIntegerField(
        default=14,
        validators=[MinValueValidator(1), MaxValueValidator(90)],
        help_text="Number of days after the visit when feedback submissions remain open."
    )

    reminder_enabled = models.BooleanField(
        default=True,
        help_text="Send one reminder email when no feedback is submitted."
    )

    reminder_delay_days = models.PositiveSmallIntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(30)],
        help_text="Days after the first feedback email to send the reminder."
    )
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Feedback Email Template"
        verbose_name_plural = "Feedback Email Template"
    
    def __str__(self):
        return "Feedback Email Template"
    
    @classmethod
    def get_template(cls):
        """Get or create the singleton template instance."""
        template, created = cls.objects.get_or_create(pk=1)
        return template


