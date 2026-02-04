from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
import datetime

from fergusonbequest.models import Attraction, VisitSlot, Booking

User = get_user_model()


class BookingAccessTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', email='alice@example.com', password='testpass')
        self.other = User.objects.create_user(username='bob', email='bob@example.com', password='testpass')
        self.attraction = Attraction.objects.create(name='Museum', slug='museum')
        self.slot = VisitSlot.objects.create(
            attraction=self.attraction,
            date=timezone.now().date() + timezone.timedelta(days=5),
            remaining=5,
        )
        # Use a different slot for Bob so we don't violate the (user, slot) active-uniqueness rule.
        self.slot2 = VisitSlot.objects.create(
            attraction=self.attraction,
            date=timezone.now().date() + timezone.timedelta(days=6),
            remaining=5,
        )
        self.booking = Booking.objects.create(attraction=self.attraction, slot=self.slot, full_name='Alice', email='alice@example.com', user=self.user)
        self.other_booking = Booking.objects.create(attraction=self.attraction, slot=self.slot2, full_name='Bob', email='bob@example.com', user=self.other)

    def test_anonymous_redirects_to_login(self):
        """Ensure anonymous users are redirected to the login page.

        Params: none

        Expected: HTTP 302 redirect to login.
        Pass: status_code == 302 and Location contains '/login/'. Fail: no redirect or wrong location.
        """
        url = reverse('booking_history')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response['Location'])

    def test_authenticated_user_sees_only_their_bookings(self):
        """Authenticated users should only see their own bookings.

        Params: authenticated user

        Expected: page loads and contains only the user's bookings.
        Pass: user's email present and other user's email absent. Fail: other user's data visible.
        """
        self.client.login(username='alice', password='testpass')
        url = reverse('booking_history')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn('alice@example.com', content)
        self.assertNotIn('bob@example.com', content)


class BookingSearchAndFiltersTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='romeo', email='romeo@example.com', password='testpass')

        today = timezone.now().date()
        past_date = today - timezone.timedelta(days=10)
        future_date = today + timezone.timedelta(days=10)
        future_date2 = today + timezone.timedelta(days=15)

        # Attractions
        self.alpha = Attraction.objects.create(name='Seed Venue Alpha', slug='seed-alpha')
        self.beta = Attraction.objects.create(name='Beta Gardens', slug='beta-gardens')

        # Slots
        self.past_slot = VisitSlot.objects.create(attraction=self.alpha, date=past_date, capacity=10, remaining=5)
        self.future_slot = VisitSlot.objects.create(attraction=self.alpha, date=future_date, capacity=10, remaining=6)
        self.future_slot2 = VisitSlot.objects.create(attraction=self.beta, date=future_date2, capacity=10, remaining=7)

        # Bookings across combinations
        self.past_active = Booking.objects.create(user=self.user, attraction=self.alpha, slot=self.past_slot, email='past@example.com')
        self.past_cancelled = Booking.objects.create(user=self.user, attraction=self.alpha, slot=self.past_slot, email='pastc@example.com', cancelled=True)
        self.future_active = Booking.objects.create(user=self.user, attraction=self.alpha, slot=self.future_slot, email='future@example.com')
        self.future_cancelled = Booking.objects.create(user=self.user, attraction=self.beta, slot=self.future_slot2, email='futurec@example.com', cancelled=True)

    def login(self):
        self.client.login(username='romeo', password='testpass')

    def test_search_matches_attraction_name(self):
        """Search by attraction name should return matching bookings.

        Params: q (substring of attraction.name)

        Expected: booking history includes attraction name matching query.
        Pass: response contains 'Seed Venue Alpha'. Fail: match absent.
        """
        self.login()
        url = reverse('booking_history') + '?q=Alpha'
        resp = self.client.get(url)
        self.assertContains(resp, 'Seed Venue Alpha')

    def test_search_matches_booking_id(self):
        """Searching by booking id should return that booking.

        Params: q (booking PK)

        Expected: booking page includes the booking id as text. Pass: id found.
        """
        self.login()
        url = reverse('booking_history') + f'?q={self.future_active.pk}'
        resp = self.client.get(url)
        self.assertContains(resp, str(self.future_active.pk))

    def test_search_matches_email(self):
        """Searching by email should return bookings with that email.

        Params: q (email string)

        Expected: booking history includes the provided email. Pass: email present.
        """
        self.login()
        url = reverse('booking_history') + '?q=future@example.com'
        resp = self.client.get(url)
        self.assertContains(resp, 'future@example.com')

    def test_filter_when_future_only_includes_future(self):
        """When=future filter shows only future bookings.

        Params: when=future

        Expected: page shows future bookings and not past ones. Pass: future present, past absent.
        """
        self.login()
        url_future = reverse('booking_history') + '?when=future'
        resp = self.client.get(url_future)
        self.assertContains(resp, 'Future Bookings')
        self.assertContains(resp, self.future_active.attraction.name)
        self.assertNotContains(resp, 'past@example.com')

    def test_filter_when_past_only_includes_past(self):
        """When=past filter shows only past bookings.

        Params: when=past

        Expected: page shows past bookings and not future ones. Pass: past present, future absent.
        """
        self.login()
        url_past = reverse('booking_history') + '?when=past'
        resp = self.client.get(url_past)
        self.assertContains(resp, 'Past Bookings')
        self.assertContains(resp, 'past@example.com')
        self.assertNotContains(resp, 'future@example.com')

    def test_status_filter_cancelled_returns_only_cancelled(self):
        """Status=cancelled returns cancelled bookings only.

        Params: status=cancelled

        Expected: only cancelled bookings present. Pass: cancelled present, active absent.
        """
        self.login()
        url = reverse('booking_history') + '?status=cancelled'
        resp = self.client.get(url)
        self.assertContains(resp, 'pastc@example.com')
        self.assertContains(resp, 'futurec@example.com')
        self.assertNotContains(resp, 'past@example.com')

    def test_status_filter_active_returns_only_active(self):
        """Status=active returns active (non-cancelled) bookings only.

        Params: status=active

        Expected: only active bookings present. Pass: active present, cancelled absent.
        """
        self.login()
        url = reverse('booking_history') + '?status=active'
        resp = self.client.get(url)
        self.assertContains(resp, 'past@example.com')
        self.assertContains(resp, 'future@example.com')
        self.assertNotContains(resp, 'futurec@example.com')

    def test_venue_filter_by_id(self):
        """Filtering by venue id returns bookings for that attraction.

        Params: venue (numeric id)

        Expected: only bookings for the given attraction shown. Pass: expected present/absent.
        """
        self.login()
        url_id = reverse('booking_history') + f'?venue={self.alpha.pk}'
        resp = self.client.get(url_id)
        self.assertContains(resp, 'Seed Venue Alpha')
        self.assertNotContains(resp, 'Beta Gardens')

    def test_venue_filter_by_slug_substring(self):
        """Filtering by venue slug substring returns matching attractions.

        Params: venue (slug fragment)

        Expected: bookings for matching attraction(s) shown. Pass: Beta Gardens present.
        """
        self.login()
        url_slug = reverse('booking_history') + '?venue=beta'
        resp = self.client.get(url_slug)
        self.assertContains(resp, 'Beta Gardens')
        self.assertNotContains(resp, 'Seed Venue Alpha')

    def test_date_range_filter_start_end(self):
        """Filtering by start/end date returns bookings within that date range.

        Params: start (ISO date), end (ISO date)

        Expected: only bookings on/within the range included. Pass: expected present/absent.
        """
        self.login()
        start = self.future_slot.date.isoformat()
        end = self.future_slot.date.isoformat()
        url = reverse('booking_history') + f'?start={start}&end={end}'
        resp = self.client.get(url)
        self.assertContains(resp, self.future_active.attraction.name)
        self.assertNotContains(resp, self.future_cancelled.attraction.name)

    def test_sorting_by_slot_date(self):
        """Sorting by slot_date orders bookings by the slot's date ascending.

        Params: sort=slot_date

        Expected: earlier booking appears before later booking in HTML. Pass: ordering correct.
        """
        self.login()
        later_slot = VisitSlot.objects.create(attraction=self.alpha, date=self.future_slot.date + timezone.timedelta(days=2), capacity=5, remaining=5)

        # Reuse the existing active booking for (self.user, self.future_slot) to avoid violating the (user, slot) uniqueness rule.
        booking_earlier = self.future_active
        booking_earlier.email = 'earlier@example.com'
        booking_earlier.save(update_fields=['email'])

        booking_later = Booking.objects.create(user=self.user, attraction=self.alpha, slot=later_slot, email='later@example.com')

        url = reverse('booking_history') + '?sort=slot_date'
        resp = self.client.get(url)
        content = resp.content.decode('utf-8')
        self.assertTrue(content.find('earlier@example.com') < content.find('later@example.com'))

    def test_invalid_date_params_are_ignored(self):
        """Ensure invalid date parameters don't crash the view.

        Params:
        - start (str), end (str): invalid ISO date strings

        Expected: booking history page loads (HTTP 200).
        Pass: response.status_code == 200. Fail: exception or non-200 returned.
        """
        self.login()
        url = reverse('booking_history') + '?start=not-a-date&end=also-not'
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_sorting_by_created_at_descending(self):
        """Verify ordering by created_at descending when sort=created_at.

        Setup: create an older and a newer booking (adjust created_at timestamps).

        Expected: newer appears before older when sort=created_at.
        Pass: new@example.com appears before old@example.com. Fail: wrong ordering.
        """
        self.login()

        # Reuse the existing active booking for (self.user, self.future_slot) to avoid violating the (user, slot) uniqueness rule.
        older = self.future_active
        older.email = 'old@example.com'
        older.created_at = timezone.now() - timezone.timedelta(days=2)
        older.save(update_fields=['email', 'created_at'])

        # Use a different slot for the newer booking so we don't create two active bookings on the same (user, slot).
        other_slot = VisitSlot.objects.create(
            attraction=self.alpha,
            date=self.future_slot.date + timezone.timedelta(days=1),
            capacity=10,
            remaining=10,
        )

        newer = Booking.objects.create(user=self.user, attraction=self.alpha, slot=other_slot, email='new@example.com')
        newer.created_at = timezone.now()
        newer.save(update_fields=['created_at'])

        url = reverse('booking_history') + '?sort=created_at'
        resp = self.client.get(url)
        content = resp.content.decode('utf-8')
        self.assertTrue(content.find('new@example.com') < content.find('old@example.com'))
