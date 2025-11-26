from django.contrib import admin
from .models import Attraction, VisitSlot, Booking, Profile

# Register your models here.
# fergusonbequest/admin.py
@admin.register(Attraction)
class AttractionAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ("name","location","per_year_limit","booking_open","booking_close")

@admin.register(VisitSlot)
class VisitSlotAdmin(admin.ModelAdmin):
    list_display = ("attraction","date","time","capacity","remaining")
    list_filter  = ("attraction",)

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("full_name","email","attraction","slot","created_at","cancelled")
    list_filter  = ("attraction","slot","cancelled")

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user","staff_guid","eligible","department")
    search_fields = ("user__username","user__email","staff_guid","department")