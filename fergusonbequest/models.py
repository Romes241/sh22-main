from django.db import models
from django.utils import timezone
from django.conf import settings
# Create your models here.
YEAR_LIMIT_DEFAULT = 3
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
    """One reservation. (Using name/email for now; can swap to auth.User later.)"""
    attraction = models.ForeignKey('Attraction', on_delete=models.CASCADE)
    slot = models.ForeignKey(VisitSlot, on_delete=models.PROTECT)
    full_name = models.CharField(max_length=120)
    email = models.EmailField()
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                              blank=True, related_name='bookings')
    agreed_terms = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    cancelled = models.BooleanField(default=False)
    ticket_code = models.CharField(max_length=16, unique=True, null=True, blank=True)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        who = self.user.username if self.user else self.full_name
        return f"{who} → {self.attraction.name} @ {self.slot}"

    @property
    def year(self):
        return self.created_at.year
    
    def save(self, *args, **kwargs):
        if not self.ticket_code:
            import uuid
            base = 'FB-' + uuid.uuid4().hex[:8].upper()
            from django.db import IntegrityError
            tries = 0
            while tries < 5:
                if not Booking.objects.filter(ticket_code=base).exists():
                    self.ticket_code = base
                    break
                base = 'FB-' + uuid.uuid4().hex[:8].upper()
                tries += 1
        super().save(*args, **kwargs)

class TicketDrawBooking(models.Model):
    """One reservation. (Using name/email for now; can swap to auth.User later.)"""
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
    ticket_code = models.CharField(max_length=16, unique=True, null=True, blank=True)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        who = self.user.username if self.user else self.full_name
        return f"{who} → {self.ticket_draw.name} @ {self.slot}"

    @property
    def year(self):
        return self.created_at.year
    
    def save(self, *args, **kwargs):
        if not self.ticket_code:
            import uuid
            base = 'FB-' + uuid.uuid4().hex[:8].upper()
            from django.db import IntegrityError
            tries = 0
            while tries < 5:
                if not Booking.objects.filter(ticket_code=base).exists():
                    self.ticket_code = base
                    break
                base = 'FB-' + uuid.uuid4().hex[:8].upper()
                tries += 1
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
