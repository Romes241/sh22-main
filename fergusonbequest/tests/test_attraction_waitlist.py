from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model

from fergusonbequest.models import Attraction, VisitSlot, AttractionWaitlistEntry
from .utils import unique_email, unique_username

User = get_user_model()


class AttractionWaitlistPersistenceTests(TestCase):
    """Test that attraction waitlist entries persist in the database."""

    def setUp(self):
        self.user = User.objects.create_user(
            username=unique_username(),
            email=unique_email(),
            password="testpass123"
        )
        self.attraction = Attraction.objects.create(
            name="Sold Out Museum",
            slug="sold-out-museum",
            attraction_type="regular"
        )
        # Create a sold-out slot
        self.slot = VisitSlot.objects.create(
            attraction=self.attraction,
            date=timezone.now().date() + timezone.timedelta(days=5),
            capacity=10,
            remaining=0
        )

    def test_join_waitlist_creates_database_entry(self):
        """Joining waitlist should create a persistent database entry.

        Params: authenticated user, sold-out attraction

        Expected: AttractionWaitlistEntry created in database.
        Pass: entry exists with correct user/attraction. Fail: entry not found.
        """
        self.client.login(username=self.user.username, password="testpass123")

        url = reverse("waiting_listattraction_join", args=[self.slot.pk])
        response = self.client.post(url)

        # Should redirect
        self.assertEqual(response.status_code, 302)

        # Entry should exist in database
        entry = AttractionWaitlistEntry.objects.filter(
            user=self.user,
            attraction=self.attraction,
            slot=self.slot,
            cancelled=False
        ).first()

        self.assertIsNotNone(entry)
        self.assertEqual(entry.user, self.user)
        self.assertEqual(entry.attraction, self.attraction)
        self.assertEqual(entry.slot, self.slot)
        self.assertFalse(entry.cancelled)
        self.assertFalse(entry.notified)

    def test_waitlist_persists_across_sessions(self):
        """Waitlist entry should persist after logout and re-login.

        Params: authenticated user with existing waitlist entry

        Expected: Entry visible after logout/login cycle.
        Pass: entry still exists with same data. Fail: entry lost.
        """
        # Join waitlist
        entry = AttractionWaitlistEntry.objects.create(
            user=self.user,
            attraction=self.attraction,
            slot=self.slot,
        )

        # Logout
        self.client.logout()

        # Login again
        self.client.login(username=self.user.username, password="testpass123")

        # Check entry still exists
        persisted_entry = AttractionWaitlistEntry.objects.filter(
            user=self.user,
            attraction=self.attraction,
            slot=self.slot,
            cancelled=False
        ).first()

        self.assertIsNotNone(persisted_entry)
        self.assertEqual(persisted_entry.id, entry.id)

    def test_leave_waitlist_marks_cancelled(self):
        """Leaving waitlist should mark entry as cancelled, not delete it.

        Params: authenticated user with active waitlist entry

        Expected: Entry marked cancelled=True, not deleted.
        Pass: entry exists with cancelled=True. Fail: entry deleted or still active.
        """
        entry = AttractionWaitlistEntry.objects.create(
            user=self.user,
            attraction=self.attraction,
            slot=self.slot,
        )

        self.client.login(username=self.user.username, password="testpass123")

        url = reverse("waiting_listattraction_leave", args=[self.slot.pk])
        response = self.client.post(url)

        # Should redirect
        self.assertEqual(response.status_code, 302)

        # Entry should still exist but be cancelled
        entry.refresh_from_db()
        self.assertTrue(entry.cancelled)

        # Should not show in active queries
        active_entry = AttractionWaitlistEntry.objects.filter(
            user=self.user,
            attraction=self.attraction,
            slot=self.slot,
            cancelled=False
        ).first()

        self.assertIsNone(active_entry)

    def test_duplicate_join_prevents_multiple_entries(self):
        """Joining waitlist twice should not create duplicate entries.

        Params: authenticated user attempting to join same waitlist twice

        Expected: Only one active entry exists.
        Pass: count of active entries == 1. Fail: multiple entries created.
        """
        self.client.login(username=self.user.username, password="testpass123")

        url = reverse("waiting_listattraction_join", args=[self.slot.pk])

        # Join twice
        self.client.post(url)
        self.client.post(url)

        # Should only have one active entry
        count = AttractionWaitlistEntry.objects.filter(
            user=self.user,
            attraction=self.attraction,
            slot=self.slot,
            cancelled=False
        ).count()

        self.assertEqual(count, 1)


class AttractionWaitlistUITests(TestCase):
    """Test that attraction detail page shows correct UI based on availability."""

    def setUp(self):
        self.user = User.objects.create_user(
            username=unique_username(),
            email=unique_email(),
            password="testpass123"
        )
        self.attraction_available = Attraction.objects.create(
            name="Available Museum",
            slug="available-museum",
            attraction_type="regular"
        )
        self.slot_available = VisitSlot.objects.create(
            attraction=self.attraction_available,
            date=timezone.now().date() + timezone.timedelta(days=5),
            capacity=10,
            remaining=5
        )

        self.attraction_sold_out = Attraction.objects.create(
            name="Sold Out Museum",
            slug="sold-out-museum",
            attraction_type="regular"
        )
        self.slot_sold_out = VisitSlot.objects.create(
            attraction=self.attraction_sold_out,
            date=timezone.now().date() + timezone.timedelta(days=5),
            capacity=10,
            remaining=0
        )

    def test_available_attraction_shows_booking_ui(self):
        """Available attraction should show booking form, not waitlist.

        Params: authenticated user, attraction with available slots

        Expected: Page contains booking UI with slot selection.
        Pass: 'Book now' button and slot dropdown present. Fail: waitlist UI shown.
        """
        self.client.login(username=self.user.username, password="testpass123")

        url = reverse("attraction", args=[self.attraction_available.pk])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")

        # Should have booking form
        self.assertIn("Select date", content)
        self.assertIn("time:", content)
        self.assertIn("Book now", content)

        # Should NOT have waitlist UI
        self.assertNotIn("Join Waiting List", content)

    def test_sold_out_attraction_shows_waitlist_ui(self):
        """Sold out attraction should show waitlist join, not booking form.

        Params: authenticated user, sold-out attraction

        Expected: Page contains waitlist join button, no booking form.
        Pass: 'Join Waiting List' button present, no slot dropdown. Fail: booking UI shown.
        """
        self.client.login(username=self.user.username, password="testpass123")

        url = reverse("attraction", args=[self.attraction_sold_out.pk])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")

        # Should have waitlist UI
        self.assertIn("Join Waiting List", content)
        self.assertIn("sold out", content.lower())

        # Should NOT have booking form
        self.assertNotIn("Select date &amp; time:", content)

    def test_on_waitlist_shows_leave_button(self):
        """User already on waitlist should see leave button.

        Params: authenticated user with active waitlist entry

        Expected: Page shows 'Leave Waiting List' button.
        Pass: leave button present, join button absent. Fail: join button shown.
        """
        self.client.login(username=self.user.username, password="testpass123")

        # Join waitlist
        AttractionWaitlistEntry.objects.create(
            user=self.user,
            attraction=self.attraction_sold_out,
            slot=self.slot_sold_out,
        )

        url = reverse("attraction", args=[self.attraction_sold_out.pk])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")

        # Should have leave button
        self.assertIn("Leave Waiting List", content)

        # Should NOT have join button
        self.assertNotIn("Join Waiting List", content)


class AttractionWaitlistAccessTests(TestCase):
    """Test access control for waitlist operations."""

    def setUp(self):
        self.user = User.objects.create_user(
            username=unique_username(),
            email=unique_email(),
            password="testpass123"
        )
        self.attraction = Attraction.objects.create(
            name="Test Museum",
            slug="test-museum",
            attraction_type="regular"
        )
        self.slot = VisitSlot.objects.create(
            attraction=self.attraction,
            date=timezone.now().date() + timezone.timedelta(days=5),
            capacity=10,
            remaining=0
        )

    def test_anonymous_user_cannot_join_waitlist(self):
        """Anonymous users should be redirected to login when joining waitlist.

        Params: unauthenticated request

        Expected: HTTP 302 redirect to login page.
        Pass: redirects to /login/. Fail: allows access or different redirect.
        """
        url = reverse("waiting_listattraction_join", args=[self.slot.pk])
        response = self.client.post(url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response["Location"])

    def test_cannot_join_waitlist_if_slots_available(self):
        """Should not allow joining waitlist when slots are still available.

        Params: authenticated user, attraction with available slots

        Expected: Error message, no entry created.
        Pass: no entry exists, error message shown. Fail: entry created.
        """
        # Make slot available
        self.slot.remaining = 5
        self.slot.save()

        self.client.login(username=self.user.username, password="testpass123")

        url = reverse("waiting_listattraction_join", args=[self.slot.pk])
        response = self.client.post(url, follow=True)

        # Should not create entry
        entry_count = AttractionWaitlistEntry.objects.filter(
            user=self.user,
            attraction=self.attraction,
            slot=self.slot,
            cancelled=False
        ).count()

        self.assertEqual(entry_count, 0)

        # Should show error message
        messages = list(response.context["messages"])
        self.assertTrue(any("still has availability" in str(m) for m in messages))


class AttractionWaitlistPageTests(TestCase):
    """Test the attraction waiting list page."""

    def setUp(self):
        self.user = User.objects.create_user(
            username=unique_username(),
            email=unique_email(),
            password="testpass123"
        )
        self.attraction1 = Attraction.objects.create(
            name="Museum A",
            slug="museum-a",
            location="Edinburgh",
            attraction_type="regular"
        )
        self.attraction2 = Attraction.objects.create(
            name="Museum B",
            slug="museum-b",
            location="Glasgow",
            attraction_type="regular"
        )
        self.slot1 = VisitSlot.objects.create(
            attraction=self.attraction1,
            date=timezone.now().date() + timezone.timedelta(days=5),
            capacity=10,
            remaining=0
        )
        self.slot2 = VisitSlot.objects.create(
            attraction=self.attraction2,
            date=timezone.now().date() + timezone.timedelta(days=6),
            capacity=10,
            remaining=0
        )

    def test_waiting_list_page_shows_user_entries(self):
        """Waiting list page should display all user's active waitlist entries.

        Params: authenticated user with multiple waitlist entries

        Expected: Page shows all active entries with attraction names.
        Pass: all attraction names present in response. Fail: entries missing.
        """
        # Create entries
        AttractionWaitlistEntry.objects.create(
            user=self.user,
            attraction=self.attraction1,
            slot=self.slot1,
        )
        AttractionWaitlistEntry.objects.create(
            user=self.user,
            attraction=self.attraction2,
            slot=self.slot2,
        )

        self.client.login(username=self.user.username, password="testpass123")

        url = reverse("waiting_listattraction")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")

        self.assertIn("Museum A", content)
        self.assertIn("Museum B", content)
        self.assertIn("Edinburgh", content)
        self.assertIn("Glasgow", content)

    def test_cancelled_entries_not_shown(self):
        """Cancelled waitlist entries should not appear on the page.

        Params: authenticated user with cancelled entry

        Expected: Cancelled entry not visible, active entry visible.
        Pass: only active entry shown. Fail: cancelled entry displayed.
        """
        # Active entry
        AttractionWaitlistEntry.objects.create(
            user=self.user,
            attraction=self.attraction1,
            slot=self.slot1,
        )

        # Cancelled entry
        AttractionWaitlistEntry.objects.create(
            user=self.user,
            attraction=self.attraction2,
            slot=self.slot2,
            cancelled=True
        )

        self.client.login(username=self.user.username, password="testpass123")

        url = reverse("waiting_listattraction")
        response = self.client.get(url)

        content = response.content.decode("utf-8")

        # Should show active entry
        self.assertIn("Museum A", content)

        # Should NOT show cancelled entry
        self.assertNotIn("Museum B", content)

    def test_empty_waitlist_shows_message(self):
        """Empty waitlist should show appropriate message.

        Params: authenticated user with no waitlist entries

        Expected: Page shows 'not on any attraction waiting lists' message.
        Pass: message present. Fail: message absent or error.
        """
        self.client.login(username=self.user.username, password="testpass123")

        url = reverse("waiting_listattraction")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "not on any attraction waiting lists")