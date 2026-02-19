import os
import sys
import django
import random
from datetime import time, timedelta
import datetime
from django.utils import timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
import datetime
import random
from datetime import time, timedelta

from django.utils import timezone
from django.contrib.auth import get_user_model

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth import get_user_model
from fergusonbequest.models import (
    Attraction,
    TicketDraw,
    TicketDrawVisitSlot,
    VisitSlot,
    Booking,
    TicketDrawBooking,
)

User = get_user_model()


def create_user(username: str):
    u, _ = User.objects.get_or_create(
        username=username,
        defaults={"email": f"{username}@test.com"},
    )
    u.set_password("password123")
    u.save()
    return u


def get_participants():
    return list(User.objects.filter(is_superuser=False, is_staff=False))


def populate():
    now = timezone.now()
    today = now.date()

    # delete everything created in this script so slugs/unique fields don't clash on rerun
    Booking.objects.all().delete()
    TicketDrawBooking.objects.all().delete()
    VisitSlot.objects.all().delete()
    TicketDrawVisitSlot.objects.all().delete()
    Attraction.objects.all().delete()
    TicketDraw.objects.all().delete()

    # create normal users
    for name in ["alice", "bob", "charlie", "david", "emma"]:
        create_user(name)

    participants = get_participants()
    if not participants:
        raise Exception("No participants found.")

    # helper to create different dates relative to now
    def dt(days):
        return now + timedelta(days=days)

    zoo_attr = Attraction.objects.create(
        slug="edinburgh-zoo",
        name="Edinburgh Zoo",
        location="Edinburgh",
        image="fergusonbequest/img/edinburgh_zoo.jpg",
        per_year_limit=3,
        booking_open=dt(-12),
        booking_close=dt(5),
    )

    safari_attr = Attraction.objects.create(
        slug="blair-drummond-safari-park",
        name="Blair Drummond Safari Park",
        location="Stirling",
        image="fergusonbequest/img/blair_drumond.jpg",
        per_year_limit=5,
        booking_open=dt(-8),
        booking_close=dt(10),
    )

    clan_attr = Attraction.objects.create(
        slug="glasgow-clan-ice-hockey",
        name="Glasgow Clan Ice Hockey",
        location="Glasgow",
        image="fergusonbequest/img/glasgow_clan.jpg",
        per_year_limit=10,
        booking_open=dt(-4),
        booking_close=dt(14),
    )

    cinema_attr = Attraction.objects.create(
        slug="ghostbusters-screening",
        name="Ghostbusters Screening",
        location="Glasgow",
        image="fergusonbequest/img/ghostbusters.jpg",
        per_year_limit=2,
        booking_open=dt(2),
        booking_close=dt(20),
    )

    # visit slots (past + future)
    slot_data = [
        (zoo_attr, today - timedelta(days=7), time(10, 0), 50, 40),
        (safari_attr, today - timedelta(days=3), time(11, 0), 30, 20),
        (clan_attr, today + timedelta(days=3), time(19, 0), 100, 80),
        (zoo_attr, today + timedelta(days=5), time(10, 0), 50, 25),
        (safari_attr, today + timedelta(days=10), time(11, 0), 30, 15),
        (cinema_attr, today + timedelta(days=5), time(20, 0), 100, 0),
    ]

    created_slots = []

    for attraction, d, t, cap, rem in slot_data:
        s = VisitSlot.objects.create(
            attraction=attraction,
            date=d,
            time=t,
            capacity=cap,
            remaining=rem,
        )
        created_slots.append(s)

    # ticket draws
    zoo_draw = TicketDraw.objects.create(
        slug="edinburgh-zoo-draw",
        name="Edinburgh Zoo",
        location="Edinburgh",
        draw_date=dt(18),
        booking_open=dt(-6),
        booking_close=dt(4),
        per_year_limit=3,
        description="Choose a slot and enter.",
        terms="Staff ID required.",
    )

    safari_draw = TicketDraw.objects.create(
        slug="blair-drummond-draw",
        name="Blair Drummond",
        location="Stirling",
        draw_date=dt(24),
        booking_open=dt(-2),
        booking_close=dt(9),
        per_year_limit=2,
        description="Choose a slot and enter.",
        terms="Winners announced before event.",
    )

    # reset winners
    zoo_draw.winner_booking = None
    zoo_draw.winner_selected_at = None
    zoo_draw.save()

    safari_draw.winner_booking = None
    safari_draw.winner_selected_at = None
    safari_draw.save()

    # draw slots
    zoo_slots = []
    for days, t, cap in [(26, time(10, 0), 5), (27, time(14, 0), 8)]:
        zoo_slots.append(
            TicketDrawVisitSlot.objects.create(
                ticket_draw=zoo_draw,
                date=today + timedelta(days=days),
                time=t,
                capacity=cap,
                remaining=cap,
            )
        )

    safari_slots = []
    for days, t, cap in [(30, time(9, 30), 5), (31, time(13, 0), 7)]:
        safari_slots.append(
            TicketDrawVisitSlot.objects.create(
                ticket_draw=safari_draw,
                date=today + timedelta(days=days),
                time=t,
                capacity=cap,
                remaining=cap,
            )
        )

    # create bookings
    for user in participants:

        past_slots = [s for s in created_slots if s.date < today and s.remaining > 0]
        future_slots = [s for s in created_slots if s.date >= today and s.remaining > 0]

        chosen_slots = []

        # make sure theres one past and one future booking
        if past_slots:
            chosen_slots.append(random.choice(past_slots))
        if future_slots:
            chosen_slots.append(random.choice(future_slots))

        # if we only got 1 (or 0) top up from anything available
        if len(chosen_slots) < 2:
            any_slots = [s for s in created_slots if s.remaining > 0]
            random.shuffle(any_slots)
            for s in any_slots:
                if len(chosen_slots) >= 2:
                    break
                if s not in chosen_slots:
                    chosen_slots.append(s)

        for slot in chosen_slots:
            if slot.remaining <= 0:
                continue

            tickets = random.choice([1, 2])
            if slot.remaining < tickets:
                tickets = 1

            is_past = slot.date < today

            # past shouldn't randomly be cancelled
            is_cancelled = False if is_past else random.choice([False, False, False, True])

            booking = Booking.objects.create(
                user=user,
                attraction=slot.attraction,
                slot=slot,
                full_name=user.username,
                email=user.email,
                num_tickets=tickets,
                agreed_terms=True,
                cancelled=is_cancelled,
            )

            if is_past:
                past_dt = datetime.datetime.combine(
                    slot.date - timedelta(days=random.randint(3, 14)),
                    datetime.time(12, 0),
                )
                booking.created_at = timezone.make_aware(past_dt)
            else:
                # booked recently for a future visit
                booking.created_at = timezone.now() - timedelta(days=random.randint(0, 5))

            booking.save(update_fields=["created_at"])

            # only consume capacity if it's actually active
            if not booking.cancelled:
                slot.remaining -= tickets
                slot.save(update_fields=["remaining"])

    # draw entries
    for user in participants:
        TicketDrawBooking.objects.create(
            ticket_draw=zoo_draw,
            slot=random.choice(zoo_slots),
            user=user,
            full_name=user.username,
            email=user.email,
            num_tickets=1,
            agreed_terms=True,
            cancelled=False,
            is_accepted=False,
        )

    # make bob winner but pending
    bob = User.objects.filter(username="bob").first()
    if bob:
        entry = TicketDrawBooking.objects.filter(ticket_draw=zoo_draw, user=bob).first()
        if entry:
            # draw is closed (booking window ended)
            zoo_draw.booking_close = timezone.now() - timedelta(days=2)
            # admin draws after it closed
            zoo_draw.winner_booking = entry
            zoo_draw.winner_selected_at = timezone.now() - timedelta(days=1)
            zoo_draw.save(update_fields=["booking_close", "winner_booking", "winner_selected_at"])
            # leave pending

    print("Populate complete.")
    print("Login as bob, to test the draw acceptance.")
    print("email: bob@test.com, password: password123")
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
