import os
import django
from datetime import time, datetime, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

django.setup()

from fergusonbequest.models import Attraction, VisitSlot, Booking

def populate():
    today = datetime.now()
    three_months = today + timedelta(days=90) # make all the open and close dates from today until 3 months from today

    #already implemented attractions manually using the admin django interface this will be used not recreated (avoids duplication)
    # there are two more attractions that were manually created too (Ghostbusters Cinema Night, Glasgow Clan Ice Hockey)
    attraction1, _ = Attraction.objects.get_or_create(
        slug="edinburgh-zoo",   # unique lookup
        defaults={
            "name": "Edinburgh Zoo",
            "location": "Edinburgh",
            "image": "images/EdZoo.jpg",
            "description": "Zoo",
            "contact_email": "info@rzss.org.uk",
            "terms": "Terms",
            "booking_open": today,
            "booking_close": three_months,
            "per_year_limit": 3,
        },
    )

    attraction2, _ = Attraction.objects.get_or_create(
        slug="blair-drummond-safari-park",   # unique lookup
        defaults={
            "name": "Blair Drummond Safari Park",
            "location": "Stirling",
            "image": "images/BlairDrummond.jpg",
            "description": "Safari Park",
            "contact_email": "enquiries@blairdrummond.com",
            "terms": "Terms",
            "booking_open": today,
            "booking_close": three_months,
            "per_year_limit": 5,
        },
    )

    visit_slot1 = VisitSlot.objects.create(attraction = attraction1, date = (today + timedelta(days=1)).date(), time = time(10,0), capacity = 100, remaining = 100)
    visit_slot2 = VisitSlot.objects.create(attraction = attraction1, date = (today + timedelta(days=4)).date(), time = time(17,45), capacity = 80, remaining = 56)
    visit_slot2 = VisitSlot.objects.create(attraction = attraction2, date = (today + timedelta(days=6)).date(), time = time(14,30), capacity = 50, remaining = 50)

    booking1 = Booking.objects.create(attraction = attraction1, slot = visit_slot1, full_name = "Ava Thompson", email = "dummy@email.com", agreed_terms = True, cancelled = False)
    booking2 = Booking.objects.create(attraction = attraction1, slot = visit_slot2, full_name = "Liam Carter", email = "dummy@email.com", agreed_terms = True, cancelled = False)
    booking3 = Booking.objects.create(attraction = attraction1, slot = visit_slot1, full_name = "Sophia Bennet", email = "dummy@email.com", agreed_terms = True, cancelled = True)
    booking4 = Booking.objects.create(attraction = attraction2, slot = visit_slot2, full_name = "Noah Hayes", email = "dummy@email.com", agreed_terms = True, cancelled = False)
    booking5 = Booking.objects.create(attraction = attraction2, slot = visit_slot2, full_name = "Isabella Brooks", email = "dummy@email.com", agreed_terms = True, cancelled = True)


if __name__ == '__main__': # only run when file is run directly
    populate()
    print("Database Populated")