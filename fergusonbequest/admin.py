from django.contrib import admin
from .models import Attraction, VisitSlot, Booking, Profile


@admin.register(Attraction)
class AttractionAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ("name", "location", "per_year_limit",
                    "booking_open", "booking_close")
    list_filter = ("booking_open", "booking_close")
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