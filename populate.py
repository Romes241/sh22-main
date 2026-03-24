import os
import sys
import random
import datetime
from collections import defaultdict
from datetime import time, timedelta
from django.db.models import Q

import django
from django.utils import timezone
from django.utils.text import slugify

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from fergusonbequest.models import (
    Attraction,
    TicketDraw,
    TicketDrawVisitSlot,
    VisitSlot,
    Booking,
    TicketDrawBooking,
    Profile,
)

User = get_user_model()

RANDOM_SEED = 42
EXTRA_USER_COUNT = 178  # plus alice + bob = 180 total users
MAX_ATTRACTION_SLOTS_PER_DAY = 3
MAX_DRAW_SLOTS_PER_DAY = 1
FUTURE_BOOKINGS_PER_USER = (0, 1)
PAST_BOOKINGS_PER_USER = (0, 1)
DRAW_ENTRY_RATE = 0.22
CANCEL_RATE = 0.08
POST_OFFICE_TICKET_RATE = 0.75

LAST_NAME_MAP = {
    "alice": "Smith",
    "bob": "Brown",
    "charlie": "Wilson",
    "david": "Taylor",
    "emma": "Anderson",
    "frank": "White",
    "grace": "Harris",
    "harry": "Clark",
    "dana": "Lewis",
    "jack": "Walker",
    "katie": "Hall",
    "liam": "Allen",
    "mason": "Young",
    "nina": "King",
    "owen": "Scott",
    "paul": "Green",
    "quinn": "Adams",
    "ruby": "Baker",
    "sam": "Nelson",
    "taylor": "Hill",
    "victor": "Carter",
    "will": "Turner",
    "xavier": "Phillips",
    "yasmin": "Parker",
    "zara": "Evans",
}

FIRST_NAMES = [
    "Ava", "Ben", "Cara", "Daniel", "Ella", "Finn", "Georgia", "Hamish", "Isla", "Jamie",
    "Kieran", "Lucy", "Millie", "Noah", "Orla", "Poppy", "Rory", "Sophie", "Theo", "Uma",
    "Violet", "William", "Zoe", "Adam", "Beth", "Calum", "Daisy", "Euan", "Freya", "Gregor",
    "Holly", "Iona", "Joshua", "Keira", "Logan", "Mia", "Nathan", "Olivia", "Phoebe", "Reuben",
    "Skye", "Toby", "Umar", "Valerie", "Wren", "Xena", "Yvonne", "Zander",
]

LAST_NAMES = [
    "Campbell", "Stewart", "Robertson", "Murphy", "Ross", "MacDonald", "Johnston", "Murray",
    "Fraser", "Graham", "Hamilton", "Kerr", "Paterson", "Douglas", "Mackenzie", "Reid",
    "Black", "Cunningham", "Davidson", "Ferguson", "Hunter", "Morrison", "Simpson", "Wallace",
]

ATTRACTION_DATA = [
    {
        "slug": "edinburgh-zoo",
        "name": "Edinburgh Zoo",
        "location": "Edinburgh",
        "image": "images/edinburgh_zoo.jpg",
        "description": "A large zoo with a wide range of animals and family-friendly attractions.",
        "duration_minutes": 180,
        "contact_email": "info@edinburghzoo.org.uk",
        "per_year_limit": 3,
    },
    {
        "slug": "blair-drummond-safari-park",
        "name": "Blair Drummond Safari Park",
        "location": "Stirling",
        "image": "images/blair_drumond.jpg",
        "description": "A family safari park with animal exhibits, adventure play areas, and outdoor activities.",
        "duration_minutes": 180,
        "contact_email": "info@blairdrummond.com",
        "per_year_limit": 5,
    },
    {
        "slug": "glasgow-clan-ice-hockey",
        "name": "Glasgow Clan Ice Hockey",
        "location": "Glasgow",
        "image": "images/glasgow_clan.jpg",
        "description": "Live ice hockey matches in Glasgow with an exciting arena atmosphere.",
        "duration_minutes": 150,
        "contact_email": "info@clanihc.com",
        "per_year_limit": 10,
    },
    {
        "slug": "ghostbusters-screening",
        "name": "Ghostbusters Screening",
        "location": "Glasgow",
        "image": "images/ghostbusters.jpg",
        "description": "A special screening event for Ghostbusters with a cinema-style viewing experience.",
        "duration_minutes": 120,
        "contact_email": "events@glasgowcinema.co.uk",
        "per_year_limit": 2,
    },
    {
        "slug": "glasgow-science-centre",
        "name": "Glasgow Science Centre",
        "location": "Glasgow",
        "image": "images/gsc.jpg",
        "description": "Interactive science exhibits, IMAX cinema, and hands-on learning for all ages.",
        "duration_minutes": 150,
        "contact_email": "info@gsc.org.uk",
        "per_year_limit": 4,
    },
    {
        "slug": "celtic-park-stadium-tour",
        "name": "Celtic Park Stadium Tour",
        "location": "Glasgow",
        "image": "images/celtic-park-stadium-tour.jpg",
        "description": "Behind-the-scenes tour of Celtic Park including dressing rooms and pitch access.",
        "duration_minutes": 90,
        "contact_email": "tours@celticfc.co.uk",
        "per_year_limit": 2,
    },
    {
        "slug": "edinburgh-castle-entry",
        "name": "Edinburgh Castle Entry",
        "location": "Edinburgh",
        "image": "images/edinburgh-castle.jpg",
        "description": "Historic castle with panoramic views and Scottish crown jewels.",
        "duration_minutes": 180,
        "contact_email": "info@edinburghcastle.scot",
        "per_year_limit": 3,
    },
    {
        "slug": "flipout-trampoline-park",
        "name": "Flip Out Trampoline Park",
        "location": "Glasgow",
        "image": "images/flipout-park.jpg",
        "description": "Indoor trampoline park with foam pits and obstacle courses.",
        "duration_minutes": 60,
        "contact_email": "info@flipout.co.uk",
        "per_year_limit": 5,
    },
    {
        "slug": "kings-theatre-show",
        "name": "King’s Theatre Live Show",
        "location": "Glasgow",
        "image": "images/kings_theatre.jpg",
        "description": "Live theatre performance including comedy, drama, or touring musicals.",
        "duration_minutes": 140,
        "contact_email": "boxoffice@kingsglasgow.co.uk",
        "per_year_limit": 2,
    },
    {
        "slug": "kelvingrove-museum",
        "name": "Kelvingrove Museum Entry",
        "location": "Glasgow",
        "image": "images/Kelvingrove_gallery.jpg",
        "description": "Museum admission with art, exhibits, and family-friendly galleries.",
        "duration_minutes": 120,
        "contact_email": "info@glasgowlife.org.uk",
        "per_year_limit": 4,
    },
    {
        "slug": "deep-sea-world",
        "name": "Deep Sea World",
        "location": "North Queensferry",
        "image": "images/deep-sea-world.jpg",
        "description": "Aquarium visit with underwater tunnel and marine life exhibits.",
        "duration_minutes": 120,
        "contact_email": "hello@deepseaworld.com",
        "per_year_limit": 3,
    },
    {
        "slug": "botanic-gardens-tour",
        "name": "Botanic Gardens Tour",
        "location": "Edinburgh",
        "image": "images/garden-tour.jpg",
        "description": "Guided seasonal tour with glasshouses and garden highlights.",
        "duration_minutes": 90,
        "contact_email": "events@rbge.org.uk",
        "per_year_limit": 2,
    },
]

DRAW_DATA = [
    {
        "slug": "edinburgh-zoo-draw",
        "name": "Edinburgh Zoo",
        "location": "Edinburgh",
        "image": "images/edinburgh_zoo.jpg",
        "description": "Choose a slot and enter for a family zoo day.",
        "terms": "Staff ID required. Winners notified by email.",
        "per_year_limit": 3,
    },
    {
        "slug": "blair-drummond-draw",
        "name": "Blair Drummond",
        "location": "Stirling",
        "image": "images/blair_drumond.jpg",
        "description": "Choose a preferred date and enter.",
        "terms": "Winners announced before the event date.",
        "per_year_limit": 2,
    },
    {
        "slug": "theatre-premium-draw",
        "name": "King’s Theatre Premium Seats",
        "location": "Glasgow",
        "image": "images/kings_theatre.jpg",
        "description": "Premium seat draw for one selected evening performance.",
        "terms": "One household win only.",
        "per_year_limit": 1,
    },
]


def make_post_office_code():
    return f"PO-{random.randint(1000, 9999)}-{random.randint(1000, 9999)}"


def convert_draw_entry_to_booking(draw_entry):
    today = timezone.localdate()

    draw = draw_entry.ticket_draw
    draw_slot = draw_entry.slot

    attraction, _ = Attraction.objects.get_or_create(
        slug=slugify(draw.name),
        defaults={
            "name": draw.name,
            "location": draw.location,
            "image": "images/edinburgh_zoo.jpg",
            "per_year_limit": getattr(draw, "per_year_limit", 3),
            "booking_open": draw.booking_open,
            "booking_close": draw.booking_close,
            "attraction_type": "weekly_event",
        },
    )

    visit_slot, _ = VisitSlot.objects.get_or_create(
        attraction=attraction,
        date=draw_slot.date,
        time=draw_slot.time,
        defaults={
            "capacity": draw_slot.capacity,
            "remaining": 0,
        },
    )

    is_past = draw_entry.slot.date < today

    ticket_type, ticket_code, box_office_notes, ticket_instructions = maybe_assign_fake_ticket(
        is_past=is_past,
        is_cancelled=False,
    )

    booking = Booking.objects.create(
        user=draw_entry.user,
        attraction=attraction,
        slot=visit_slot,
        full_name=f"{draw_entry.user.first_name} {draw_entry.user.last_name}".strip() or draw_entry.user.username,
        email=draw_entry.user.email,
        num_tickets=draw_entry.num_tickets,
        agreed_terms=True,
        cancelled=False,
        ticket_type=ticket_type,
        ticket_code=ticket_code,
        box_office_notes=box_office_notes,
        ticket_instructions=ticket_instructions,
    )

    draw_entry.is_accepted = True
    draw_entry.converted_booking = booking
    draw_entry.save(update_fields=["is_accepted", "converted_booking"])

    return booking

def create_named_user(username: str):
    first = username.capitalize()
    last = LAST_NAME_MAP.get(username.lower(), "Staff")
    user, _ = User.objects.get_or_create(username=username, defaults={"email": f"{username}@test.com"})
    user.first_name = first
    user.last_name = last
    user.email = f"{username}@test.com"
    user.is_staff = False
    user.is_superuser = False
    user.set_password("password123")
    user.save()

    profile, _ = Profile.objects.get_or_create(user=user)
    profile.staff_guid = f"G{random.randint(100000, 999999)}"
    profile.save()
    return user


def create_random_user(index: int):
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    username = f"{first.lower()}{last.lower()}{index:03d}"
    user, _ = User.objects.get_or_create(username=username, defaults={"email": f"{username}@test.com"})
    user.first_name = first
    user.last_name = last
    user.email = f"{username}@test.com"
    user.is_staff = False
    user.is_superuser = False
    user.set_password("password123")
    user.save()

    profile, _ = Profile.objects.get_or_create(user=user)
    profile.staff_guid = f"G{random.randint(100000, 999999)}"
    profile.save()
    return user


def reset_data():
    Booking.objects.all().delete()
    TicketDrawBooking.objects.all().delete()
    VisitSlot.objects.all().delete()
    TicketDrawVisitSlot.objects.all().delete()
    Attraction.objects.all().delete()
    TicketDraw.objects.all().delete()


def create_attractions(now):
    attractions = []
    for item in ATTRACTION_DATA:
        attractions.append(
            Attraction.objects.create(
                slug=item["slug"],
                name=item["name"],
                location=item["location"],
                image=item["image"],
                description=item["description"],
                duration_minutes=item["duration_minutes"],
                contact_email=item["contact_email"],
                per_year_limit=item["per_year_limit"],
                booking_open=now + timedelta(days=random.randint(-21, -4)),
                booking_close=now + timedelta(days=random.randint(8, 35)),
            )
        )
    return attractions


def pick_day_with_limit(candidate_offsets, counts, limit):
    available = [offset for offset in candidate_offsets if counts[offset] < limit]
    if not available:
        return None
    offset = random.choice(available)
    counts[offset] += 1
    return offset


def create_visit_slots(attractions, today):
    created_slots = []
    daily_counts = defaultdict(int)
    past_offsets = list(range(-12, -1))
    future_offsets = list(range(2, 46))
    slot_times = [time(10, 0), time(11, 30), time(13, 0), time(15, 0), time(19, 30)]

    for attraction in attractions:
        future_slot_total = random.choice([2, 3])
        past_slot_total = 1

        used_offsets = set()

        for _ in range(future_slot_total):
            remaining_offsets = [o for o in future_offsets if o not in used_offsets]
            offset = pick_day_with_limit(remaining_offsets, daily_counts, MAX_ATTRACTION_SLOTS_PER_DAY)
            if offset is None:
                break
            used_offsets.add(offset)
            capacity = random.choice([20, 25, 30, 40, 50, 60])
            created_slots.append(
                VisitSlot.objects.create(
                    attraction=attraction,
                    date=today + timedelta(days=offset),
                    time=random.choice(slot_times),
                    capacity=capacity,
                    remaining=capacity,
                )
            )

        for _ in range(past_slot_total):
            remaining_offsets = [o for o in past_offsets if o not in used_offsets]
            if not remaining_offsets:
                break
            offset = random.choice(remaining_offsets)
            used_offsets.add(offset)
            capacity = random.choice([20, 25, 30, 40, 50])
            remaining = random.randint(0, max(2, capacity // 4))
            created_slots.append(
                VisitSlot.objects.create(
                    attraction=attraction,
                    date=today + timedelta(days=offset),
                    time=random.choice(slot_times[:-1]),
                    capacity=capacity,
                    remaining=remaining,
                )
            )

    return created_slots


def create_draws(now, today):
    draw_lookup = {}
    draw_slot_lookup = {}
    draw_day_counts = defaultdict(int)
    draw_offsets = list(range(24, 56))
    draw_times = [time(9, 30), time(11, 0), time(13, 0), time(15, 0), time(18, 30)]

    for draw_info in DRAW_DATA:
        draw = TicketDraw.objects.create(
            slug=draw_info["slug"],
            name=draw_info["name"],
            location=draw_info["location"],
            image=draw_info.get("image"),
            draw_date=now + timedelta(days=random.randint(18, 36)),
            booking_open=now + timedelta(days=random.randint(-10, -3)),
            booking_close=now + timedelta(days=random.randint(4, 14)),
            per_year_limit=draw_info["per_year_limit"],
            description=draw_info["description"],
            terms=draw_info["terms"],
        )

        slot_count = 1
        slots = []
        used_offsets = set()
        for _ in range(slot_count):
            remaining_offsets = [o for o in draw_offsets if o not in used_offsets]
            offset = pick_day_with_limit(remaining_offsets, draw_day_counts, MAX_DRAW_SLOTS_PER_DAY)
            if offset is None:
                break
            used_offsets.add(offset)
            capacity = random.choice([5, 6, 8, 10, 12])
            slots.append(
                TicketDrawVisitSlot.objects.create(
                    ticket_draw=draw,
                    date=today + timedelta(days=offset),
                    time=random.choice(draw_times),
                    capacity=capacity,
                    remaining=capacity,
                )
            )

        draw_lookup[draw.slug] = draw
        draw_slot_lookup[draw.slug] = slots

    return draw_lookup, draw_slot_lookup

def pick_booking_timestamp(slot_date, now, is_past):
    if is_past:
        days_before = random.randint(3, 21)
        hour = random.choice([9, 10, 11, 12, 14, 16])
        booked_at = datetime.datetime.combine(slot_date - timedelta(days=days_before), time(hour, 0))
        return timezone.make_aware(booked_at)
    return now - timedelta(days=random.randint(0, 10), hours=random.randint(0, 23))


def force_entire_attraction_sold_out(created_slots, attraction_slug="celtic-park-stadium-tour"):
    sold_out_slots = []

    for slot in created_slots:
        if slot.attraction.slug == attraction_slug and slot.date >= timezone.localdate():
            slot.remaining = 0
            slot.save(update_fields=["remaining"])
            sold_out_slots.append(slot)

    return sold_out_slots

def maybe_assign_fake_ticket(is_past, is_cancelled):
    if is_cancelled:
        return None, None, "", ""

    roll = random.random()

    if is_past or roll < 0.35:
        return "codes", make_post_office_code(), "", ""

    if roll < 0.55:
        return "box_office", None, "Show booking reference and staff ID.", ""

    if roll < 0.75:
        return "instructions", None, "", "Show staff ID at entrance. Arrive 15 minutes early."

    return None, None, "", ""


def create_booking_for_slot(user, slot, today, now, force_cancelled=None, force_tickets=None):
    if slot.remaining <= 0:
        return None

    tickets = force_tickets or random.choice([1, 2])
    tickets = min(tickets, slot.remaining)
    if tickets <= 0:
        return None

    is_past = slot.date < today
    is_cancelled = (False if is_past else random.random() < CANCEL_RATE) if force_cancelled is None else force_cancelled
    ticket_type, ticket_code, box_office_notes, ticket_instructions = maybe_assign_fake_ticket(is_past, is_cancelled)
    booking = Booking.objects.create(
        user=user,
        attraction=slot.attraction,
        slot=slot,
        full_name=f"{user.first_name} {user.last_name}".strip() or user.username,
        email=user.email,
        num_tickets=tickets,
        agreed_terms=True,
        cancelled=is_cancelled,
        ticket_type=ticket_type,
        ticket_code=ticket_code,
        box_office_notes=box_office_notes,
        ticket_instructions=ticket_instructions,
    )
    booking.created_at = pick_booking_timestamp(slot.date, now, is_past)
    booking.save(update_fields=["created_at"])

    if not is_cancelled:
        slot.remaining = max(0, slot.remaining - tickets)
        slot.save(update_fields=["remaining"])

    return booking


def create_general_bookings(users, created_slots, today, now, exclude_usernames=None):
    exclude_usernames = set(exclude_usernames or [])
    past_slots = [s for s in created_slots if s.date < today and s.remaining > 0]
    future_slots = [s for s in created_slots if s.date >= today and s.remaining > 0]

    total_created = 0
    for user in users:
        if user.username in exclude_usernames:
            continue

        selected_slots = []
        random.shuffle(future_slots)
        random.shuffle(past_slots)

        selected_slots.extend(future_slots[: random.randint(*FUTURE_BOOKINGS_PER_USER)])
        selected_slots.extend(past_slots[: random.randint(*PAST_BOOKINGS_PER_USER)])

        seen_slot_ids = set()
        for slot in selected_slots:
            if slot.id in seen_slot_ids or slot.remaining <= 0:
                continue
            seen_slot_ids.add(slot.id)
            if create_booking_for_slot(user, slot, today, now):
                total_created += 1

    return total_created


def create_alice_bob_bookings(alice, bob, created_slots, today, now):
    count = 0
    past_slots = [s for s in created_slots if s.date < today and s.remaining > 0]
    future_slots = [s for s in created_slots if s.date >= today and s.remaining > 0]

    def pick_slot(slots, used_ids, attraction_slug=None):
        candidates = [s for s in slots if s.id not in used_ids and (attraction_slug is None or s.attraction.slug == attraction_slug)]
        return candidates[0] if candidates else None

    alice_used = set()
    bob_used = set()

    alice_slots = [
        pick_slot(future_slots, alice_used, "edinburgh-zoo") or pick_slot(future_slots, alice_used),
        pick_slot(past_slots, alice_used, "blair-drummond-safari-park") or pick_slot(past_slots, alice_used),
    ]
    for slot in alice_slots:
        if slot:
            alice_used.add(slot.id)
            if create_booking_for_slot(alice, slot, today, now, force_cancelled=False, force_tickets=1 if slot.date < today else 2):
                count += 1

    bob_slots = [
        pick_slot(future_slots, bob_used, "glasgow-clan-ice-hockey") or pick_slot(future_slots, bob_used),
        pick_slot(future_slots, bob_used, "celtic-park-stadium-tour") or pick_slot(future_slots, bob_used),
        pick_slot(past_slots, bob_used, "edinburgh-castle-entry") or pick_slot(past_slots, bob_used),
    ]
    for idx, slot in enumerate(bob_slots):
        if slot:
            bob_used.add(slot.id)
            cancelled = True if idx == 1 else False
            if create_booking_for_slot(bob, slot, today, now, force_cancelled=cancelled, force_tickets=1 if slot.date < today else 2):
                count += 1

    return count


def create_draw_entries(users, draw_lookup, draw_slot_lookup):
    total_entries = 0

    for draw_slug, draw in draw_lookup.items():
        draw_slots = draw_slot_lookup[draw_slug]
        if not draw_slots:
            continue

        entrants = [u for u in users if u.username not in {"alice", "bob"} and random.random() < DRAW_ENTRY_RATE]
        random.shuffle(entrants)
        entrants = entrants[: random.randint(8, 18)]

        for user in entrants:
            slot = random.choice(draw_slots)
            if slot.remaining <= 0:
                continue
            num_tickets = min(random.choice([1, 1, 2]), slot.remaining)
            if num_tickets <= 0:
                continue

            TicketDrawBooking.objects.create(
                ticket_draw=draw,
                slot=slot,
                user=user,
                full_name=f"{user.first_name} {user.last_name}".strip() or user.username,
                email=user.email,
                num_tickets=num_tickets,
                agreed_terms=True,
                cancelled=False,
                is_accepted=False,
            )
            slot.remaining = max(0, slot.remaining - num_tickets)
            slot.save(update_fields=["remaining"])
            total_entries += 1

        draw.booking_close = timezone.now() - timedelta(days=1)
        draw.save(update_fields=["booking_close"])

    zoo_draw = draw_lookup.get("edinburgh-zoo-draw")
    zoo_slots = draw_slot_lookup.get("edinburgh-zoo-draw", [])
    alice = User.objects.filter(username="alice").first()
    bob = User.objects.filter(username="bob").first()

    if zoo_draw and alice and bob and zoo_slots:
        alice_slot = zoo_slots[0]
        bob_slot = zoo_slots[1] if len(zoo_slots) > 1 else zoo_slots[0]

        alice_entry = TicketDrawBooking.objects.create(
            ticket_draw=zoo_draw,
            slot=alice_slot,
            user=alice,
            full_name=f"{alice.first_name} {alice.last_name}",
            email=alice.email,
            num_tickets=1,
            agreed_terms=True,
            cancelled=False,
            is_accepted=False,
        )
        bob_entry = TicketDrawBooking.objects.create(
            ticket_draw=zoo_draw,
            slot=bob_slot,
            user=bob,
            full_name=f"{bob.first_name} {bob.last_name}",
            email=bob.email,
            num_tickets=1,
            agreed_terms=True,
            cancelled=False,
            is_accepted=False,
        )

        zoo_draw.winner_booking = bob_entry
        zoo_draw.winner_selected_at = timezone.now() - timedelta(days=1)
        zoo_draw.booking_close = timezone.now() - timedelta(days=2)
        zoo_draw.save(update_fields=["winner_booking", "winner_selected_at", "booking_close"])

        convert_draw_entry_to_booking(alice_entry)
        total_entries += 2

    # Ensure at least one NON-zoo draw is open
    open_draw = (
        TicketDraw.objects
        .exclude(slug="edinburgh-zoo-draw")
        .first()
    )
    if open_draw:
        open_draw.booking_close = timezone.now() + timedelta(days=5)
        open_draw.save(update_fields=["booking_close"])

    return total_entries

def populate():
    random.seed(RANDOM_SEED)

    site = Site.objects.get_current()
    site.domain = "127.0.0.1:8000"
    site.name = "Local Development"
    site.save()

    now = timezone.now()
    today = now.date()

    reset_data()

    alice = create_named_user("alice")
    bob = create_named_user("bob")
    extra_users = [create_random_user(i) for i in range(1, EXTRA_USER_COUNT + 1)]
    all_users = [alice, bob] + extra_users

    attractions = create_attractions(now)
    created_slots = create_visit_slots(attractions, today)
    draw_lookup, draw_slot_lookup = create_draws(now, today)

    general_count = create_general_bookings(
        all_users,
        created_slots,
        today,
        now,
        exclude_usernames={"alice", "bob"},
    )
    special_count = create_alice_bob_bookings(alice, bob, created_slots, today, now)
    draw_count = create_draw_entries(all_users, draw_lookup, draw_slot_lookup)

    sold_out_slots = force_entire_attraction_sold_out(
        created_slots,
        "celtic-park-stadium-tour",
    )

    print("Populate complete.")
    print(f"Users created/updated: {len(all_users)}")
    print(f"Attractions created: {len(attractions)}")
    print(f"Visit slots created: {len(created_slots)}")
    print(f"Ticket draws created: {len(draw_lookup)}")
    print(f"Regular bookings created: {general_count + special_count}")
    print(f"Draw entries created: {draw_count}")
    print(f"Forced sold out slots: {len(sold_out_slots)}")

    # Unticketed check
    converted_booking_ids = TicketDrawBooking.objects.filter(
        converted_booking__isnull=False
    ).values_list("converted_booking_id", flat=True)

    today = timezone.localdate()

    unticketed = 0
    qs = Booking.objects.filter(
        cancelled=False,
        slot__date__gte=today,
    ).exclude(id__in=converted_booking_ids)

    for b in qs:
        is_ticketed = any([
            b.ticket_sent,
            b.ticket_code,
            getattr(b, "ticket_qr_value", ""),
            getattr(b, "generic_booking_code", ""),
            getattr(b, "ticket_instructions", ""),
            getattr(b, "box_office_notes", ""),
            hasattr(b, "tickets") and b.tickets.exists(),
            b.ticket_type in {
                "box_office",
                "codes",
                "pdf_template",
                "qr_individual",
                "instructions",
                "booking_code",
            },
        ])
        if not is_ticketed:
            unticketed += getattr(b, "num_tickets", 1) or 1

    print(f"Number of unticketed bookings after script: {unticketed}")

if __name__ == "__main__":
    populate()
