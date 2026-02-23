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
import datetime
from django.utils import timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

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

if __name__ == "__main__":
    populate()
