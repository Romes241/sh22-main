import os
import django
from datetime import time, timedelta
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from fergusonbequest.models import Attraction, TicketDraw, TicketDrawVisitSlot, VisitSlot

def populate():
    """
    Populates:
    - 3 Available Attractions
    - 1 SOLD OUT Attraction (Ghostbusters)
    - 2 Ticket Draws (with custom terms & booking info)
    """
    today = timezone.now().date()
    draw_closing = timezone.now() + timedelta(days=14)
    standard_draw_date = today + timedelta(days=25)

    # --- 1. EDINBURGH ZOO (Available) ---
    zoo_attr, _ = Attraction.objects.get_or_create(
        slug="edinburgh-zoo",
        defaults={
            "name": "Edinburgh Zoo",
            "location": "Edinburgh",
            "image": "fergusonbequest/img/edinburgh_zoo.jpg",
            "per_year_limit": 3
        }
    )
    VisitSlot.objects.get_or_create(
        attraction=zoo_attr, date=today + timedelta(days=5), time=time(10, 00),
        defaults={"capacity": 50, "remaining": 25}
    )

    # --- 2. BLAIR DRUMMOND (Available) ---
    safari_attr, _ = Attraction.objects.get_or_create(
        slug="blair-drummond-safari-park",
        defaults={
            "name": "Blair Drummond Safari Park",
            "location": "Stirling",
            "image": "fergusonbequest/img/blair_drumond.jpg",
            "per_year_limit": 5
        }
    )
    VisitSlot.objects.get_or_create(
        attraction=safari_attr, date=today + timedelta(days=10), time=time(11, 00),
        defaults={"capacity": 30, "remaining": 15}
    )

    # --- 3. GLASGOW CLAN (Available) ---
    clan_attr, _ = Attraction.objects.get_or_create(
        slug="glasgow-clan-ice-hockey",
        defaults={
            "name": "Glasgow Clan Ice Hockey",
            "location": "Glasgow",
            "image": "fergusonbequest/img/glasgow_clan.jpg",
            "per_year_limit": 10
        }
    )
    VisitSlot.objects.get_or_create(
        attraction=clan_attr, date=today + timedelta(days=3), time=time(19, 00),
        defaults={"capacity": 100, "remaining": 80}
    )

    # --- 4. GHOSTBUSTERS (SOLD OUT) ---
    cinema, _ = Attraction.objects.get_or_create(
        slug="ghostbusters-screening",
        defaults={
            "name": "Ghostbusters Screening",
            "location": "Glasgow",
            "image": "fergusonbequest/img/ghostbusters.jpg",
            "per_year_limit": 2
        }
    )
    VisitSlot.objects.get_or_create(
        attraction=cinema, date=today + timedelta(days=5), time=time(20, 00),
        defaults={"capacity": 100, "remaining": 0} # Sold Out
    )

    # --- TICKET DRAW 1: EDINBURGH ZOO ---
    zoo_draw, _ = TicketDraw.objects.get_or_create(
        slug="edinburgh-zoo-draw",
        defaults={
            "name": "Edinburgh Zoo (Draw)",
            "location": "Edinburgh",
            "draw_date": standard_draw_date,
            "booking_open": timezone.now(),
            "booking_close": draw_closing,
            "per_year_limit": 3,
            "description": "1. Pick your preferred weekend slot below. 2. Choose up to 3 tickets for your family. 3. Click 'Enter Draw' to join the waitlist.",
            "terms": "Winners must present staff ID. Tickets are non-transferable."
        }
    )
    zoo_slots = [
        {"days": 26, "time": time(10, 0), "cap": 1},
        {"days": 27, "time": time(14, 0), "cap": 8},
        {"days": 28, "time": time(11, 0), "cap": 7},
    ]
    for slot in zoo_slots:
        TicketDrawVisitSlot.objects.get_or_create(
            ticket_draw=zoo_draw,
            date=today + timedelta(days=slot["days"]),
            time=slot["time"],
            defaults={"capacity": slot["cap"], "remaining": slot["cap"]}
        )

    # --- TICKET DRAW 2: BLAIR DRUMMOND ---
    safari_draw, _ = TicketDraw.objects.get_or_create(
        slug="blair-drummond-draw",
        defaults={
            "name": "Blair Drummond (Draw)",
            "location": "Stirling",
            "draw_date": standard_draw_date,
            "booking_open": timezone.now(),
            "booking_close": draw_closing,
            "per_year_limit": 2,
            "description": "1. Select a vehicle safari date. 2. One car entry covers up to 5 people. 3. Join the waitlist now.",
            "terms": "No soft-top cars permitted in the lion reserve. Winners announced 7 days before the event."
        }
    )
    safari_slots = [
        {"days": 30, "time": time(9, 30), "cap": 13},
        {"days": 31, "time": time(13, 0), "cap": 5},
        {"days": 32, "time": time(10, 0), "cap": 7},
    ]
    for slot in safari_slots:
        TicketDrawVisitSlot.objects.get_or_create(
            ticket_draw=safari_draw,
            date=today + timedelta(days=slot["days"]),
            time=slot["time"],
            defaults={"capacity": slot["cap"], "remaining": slot["cap"]}
        )

    print("Done populating")

if __name__ == '__main__':
    populate()