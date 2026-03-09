from django.contrib import admin
from .models import (
    Attraction,
    VisitSlot,
    Booking,
    Profile,
    TicketDraw,
    TicketDrawBooking,
    TicketDrawVisitSlot,
    AttractionSuggestion,
    AttractionWaitlistEntry,
    DiscountCode,   # ← 确保导入
)


@admin.register(Attraction)
class AttractionAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ("name", "location", "attraction_type", "per_year_limit",
                    "booking_open", "booking_close")
    list_filter = ("attraction_type", "booking_open", "booking_close")
    search_fields = ("name", "slug", "location")


@admin.register(VisitSlot)
class VisitSlotAdmin(admin.ModelAdmin):
    list_display = ("attraction", "date", "time", "capacity", "remaining")
    list_filter = ("attraction", "date")
    ordering = ("date", "time")


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("full_name", "email", "attraction",
                    "slot", "created_at", "cancelled")
    list_filter = ("attraction", "slot", "cancelled")
    search_fields = ("full_name", "email")


@admin.register(TicketDraw)
class TicketDrawAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ("name", "location", "attraction_type", "per_year_limit",
                    "booking_open", "booking_close", "draw_date")
    list_filter = ("attraction_type", "booking_open", "booking_close")
    search_fields = ("name", "slug", "location")


@admin.register(TicketDrawBooking)
class TicketDrawBookingAdmin(admin.ModelAdmin):
    list_display = ("full_name", "email", "ticket_draw",
                    "slot", "created_at", "cancelled")
    list_filter = ("ticket_draw", "slot", "cancelled")
    search_fields = ("full_name", "email")


@admin.register(TicketDrawVisitSlot)
class TicketDrawVisitSlotAdmin(admin.ModelAdmin):
    list_display = ("ticket_draw", "date", "time", "capacity", "remaining")
    list_filter = ("ticket_draw", "date")
    ordering = ("date", "time")


@admin.register(AttractionSuggestion)
class AttractionSuggestionAdmin(admin.ModelAdmin):
    list_display = ("name", "status", "submitted_by", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("name", "description", "why_recommended", "location", "website_url")
    ordering = ("-created_at",)


@admin.register(AttractionWaitlistEntry)
class AttractionWaitlistEntryAdmin(admin.ModelAdmin):
    list_display = ("user", "attraction", "created_at", "cancelled", "notified")
    list_filter = ("cancelled", "notified", "created_at", "attraction")
    search_fields = ("user__username", "user__email", "attraction__name")
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)


@admin.register(DiscountCode)
class DiscountCodeAdmin(admin.ModelAdmin):
    list_display = ("title", "code", "is_active", "valid_until")
    list_filter = ("is_active",)
    search_fields = ("title", "code")