import os
import django
import datetime
import random
from datetime import time, timedelta

from django.utils import timezone
from django.contrib.auth import get_user_model

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from fergusonbequest.models import (
    Attraction,
    TicketDraw,
    TicketDrawVisitSlot,
    VisitSlot,
    TicketDrawBooking,
)

RESET_TEST_DATA = True


def next_monday(d: datetime.date) -> datetime.date:
    """Return the next Monday after date d (not including today)."""
    days_ahead = (7 - d.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    return d + timedelta(days=days_ahead)

def make_dt(date_obj, t):
    return timezone.make_aware(datetime.datetime.combine(date_obj, t))



def reset_visit_slots_for_attraction(attraction: Attraction):
    VisitSlot.objects.filter(attraction=attraction).delete()


def reset_draw_slots(draw: TicketDraw):
    TicketDrawVisitSlot.objects.filter(ticket_draw=draw).delete()


def reset_bookings_for_draw(draw: TicketDraw, usernames: list[str]):
    TicketDrawBooking.objects.filter(ticket_draw=draw, user__username__in=usernames).delete()


def populate():
    """
    Populates test data:
        Attractions + VisitSlots (next week)
        Two Ticket Draws:
            Zoo draw: OPEN now ( users can still join)
            Safari draw: CLOSED already ( admin can run)
        Fake users + fake TicketDrawBooking entries for both draws
    """

    now = timezone.now()
    today = timezone.localdate()

    # next week dates for attractions/visit slots
    mon = next_monday(today)
    tue = mon + timedelta(days=1)
    wed = mon + timedelta(days=2)
    thu = mon + timedelta(days=3)
    fri = mon + timedelta(days=4)

    # attractions for next week
    zoo_attr, _ = Attraction.objects.update_or_create(
        slug="edinburgh-zoo",
        defaults={
            "name": "Edinburgh Zoo",
            "location": "Edinburgh",
            "image": "fergusonbequest/img/edinburgh_zoo.jpg",
            "per_year_limit": 3,
        },
    )
    reset_visit_slots_for_attraction(zoo_attr)
    VisitSlot.objects.create(
        attraction=zoo_attr,
        date=tue,
        time=time(10, 0),
        capacity=50,
        remaining=25,
    )

    safari_attr, _ = Attraction.objects.update_or_create(
        slug="blair-drummond-safari-park",
        defaults={
            "name": "Blair Drummond Safari Park",
            "location": "Stirling",
            "image": "fergusonbequest/img/blair_drumond.jpg",
            "per_year_limit": 5,
        },
    )
    reset_visit_slots_for_attraction(safari_attr)
    VisitSlot.objects.create(
        attraction=safari_attr,
        date=thu,
        time=time(11, 0),
        capacity=30,
        remaining=15,
    )

    clan_attr, _ = Attraction.objects.update_or_create(
        slug="glasgow-clan-ice-hockey",
        defaults={
            "name": "Glasgow Clan Ice Hockey",
            "location": "Glasgow",
            "image": "fergusonbequest/img/glasgow_clan.jpg",
            "per_year_limit": 10,
        },
    )
    reset_visit_slots_for_attraction(clan_attr)
    VisitSlot.objects.create(
        attraction=clan_attr,
        date=wed,
        time=time(19, 0),
        capacity=100,
        remaining=80,
    )

    cinema_attr, _ = Attraction.objects.update_or_create(
        slug="ghostbusters-screening",
        defaults={
            "name": "Ghostbusters Screening",
            "location": "Glasgow",
            "image": "fergusonbequest/img/ghostbusters.jpg",
            "per_year_limit": 2,
        },
    )
    reset_visit_slots_for_attraction(cinema_attr)
    VisitSlot.objects.create(
        attraction=cinema_attr,
        date=fri,
        time=time(20, 0),
        capacity=100,
        remaining=0,
    )

    # draws (one open, one closed)

    # Zoo draw: OPEN now (opened yesterday, closes in 5 days)
    zoo_open = now - timedelta(days=1)
    zoo_close = now + timedelta(days=5)

    # Safari draw: CLOSED already (opened 7 days ago, closed 1 hour ago)
    safari_open = now - timedelta(days=7)
    safari_close = now - timedelta(hours=1)

    zoo_draw_date = zoo_close + timedelta(days=1)
    safari_draw_date = safari_close + timedelta(days=1)

    visit_base = mon + timedelta(days=14)

    zoo_draw, _ = TicketDraw.objects.update_or_create(
        slug="edinburgh-zoo-draw",
        defaults={
            "name": "Edinburgh Zoo (Draw)",
            "location": "Edinburgh",
            "draw_date": zoo_draw_date,
            "booking_open": zoo_open,
            "booking_close": zoo_close,
            "per_year_limit": 3,
            "description": (
                "1. Pick your preferred weekend slot below. "
                "2. Choose up to 3 tickets for your family. "
                "3. Click 'Enter Draw' to join the waitlist."
            ),
            "terms": "Winners must present staff ID. Tickets are non-transferable.",
        },
    )

    reset_draw_slots(zoo_draw)
    for s in [
        {"date": visit_base + timedelta(days=0), "time": time(10, 0), "cap": 8},
        {"date": visit_base + timedelta(days=1), "time": time(14, 0), "cap": 8},
        {"date": visit_base + timedelta(days=2), "time": time(11, 0), "cap": 8},
    ]:
        TicketDrawVisitSlot.objects.create(
            ticket_draw=zoo_draw,
            date=s["date"],
            time=s["time"],
            capacity=s["cap"],
            remaining=s["cap"],
        )

    safari_draw, _ = TicketDraw.objects.update_or_create(
        slug="blair-drummond-draw",
        defaults={
            "name": "Blair Drummond (Draw)",
            "location": "Stirling",
            "draw_date": safari_draw_date,
            "booking_open": safari_open,
            "booking_close": safari_close,
            "per_year_limit": 2,
            "description": (
                "1. Select a vehicle safari date. "
                "2. One car entry covers up to 5 people. "
                "3. Join the waitlist now."
            ),
            "terms": (
                "No soft-top cars permitted in the lion reserve. "
                "Winners announced 7 days before the event."
            ),
        },
    )

    reset_draw_slots(safari_draw)
    for s in [
        {"date": visit_base + timedelta(days=3), "time": time(9, 30), "cap": 10},
        {"date": visit_base + timedelta(days=4), "time": time(13, 0), "cap": 10},
        {"date": visit_base + timedelta(days=5), "time": time(10, 0), "cap": 10},
    ]:
        TicketDrawVisitSlot.objects.create(
            ticket_draw=safari_draw,
            date=s["date"],
            time=s["time"],
            capacity=s["cap"],
            remaining=s["cap"],
        )

    # fake users and bookings
    User = get_user_model()

    admin_user, _ = User.objects.get_or_create(
        username="admin_test",
        defaults={"email": "admin_test@example.com"},
    )
    admin_user.set_password("test1234")
    admin_user.is_staff = True
    admin_user.is_superuser = True
    admin_user.save()

    fake_users_data = [
        ("alice", "alice@test.com"),
        ("bob", "bob@test.com"),
        ("charlie", "charlie@test.com"),
        ("david", "david@test.com"),
        ("emma", "emma@test.com"),
    ]

    fake_users = []
    for username, email in fake_users_data:
        u, _ = User.objects.get_or_create(username=username, defaults={"email": email})
        u.set_password("test1234")
        u.save()
        fake_users.append(u)

    usernames = [u.username for u in fake_users]

    if RESET_TEST_DATA:
        reset_bookings_for_draw(zoo_draw, usernames)
        reset_bookings_for_draw(safari_draw, usernames)

    zoo_draw_slots = list(TicketDrawVisitSlot.objects.filter(ticket_draw=zoo_draw))
    safari_draw_slots = list(TicketDrawVisitSlot.objects.filter(ticket_draw=safari_draw))

    if not zoo_draw_slots or not safari_draw_slots:
        raise ValueError("TicketDrawVisitSlot(s) missing — create draw slots before creating bookings.")

    for u in fake_users:
        TicketDrawBooking.objects.update_or_create(
            ticket_draw=zoo_draw,
            user=u,
            defaults={
                "cancelled": False,
                "full_name": u.username.title(),
                "email": u.email,
                "num_tickets": random.choice([1, 2, 3]),
                "slot": random.choice(zoo_draw_slots),
            },
        )

        TicketDrawBooking.objects.update_or_create(
            ticket_draw=safari_draw,
            user=u,
            defaults={
                "cancelled": False,
                "full_name": u.username.title(),
                "email": u.email,
                "num_tickets": random.choice([1, 2]),
                "slot": random.choice(safari_draw_slots),
            },
        )

    print("Done populating.")
    print(f"Zoo draw:    OPEN now  | open={zoo_open} close={zoo_close}")
    print(f"Safari draw: CLOSED    | open={safari_open} close={safari_close}")
    print("Fake users created: admin_test +", ", ".join(usernames))
    print("Password for all test users: test1234")


if __name__ == "__main__":
    populate()
