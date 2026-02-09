import threading
import random
import time
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import transaction, close_old_connections
from django.db.models import F
from django.db.models.functions import Least
from django.urls import reverse
from django.db.utils import OperationalError

from fergusonbequest.models import Attraction, VisitSlot, Booking

User = get_user_model()


class CancelBookingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='bob', email='bob@example.com', password='testpass')
        self.other = User.objects.create_user(username='other', email='other@example.com', password='testpass')
        self.attraction = Attraction.objects.create(name='Gallery', slug='gallery')
        today = timezone.now().date()
        self.slot_future = VisitSlot.objects.create(attraction=self.attraction, date=today + timezone.timedelta(days=5), capacity=2, remaining=1)
        self.slot_past = VisitSlot.objects.create(attraction=self.attraction, date=today - timezone.timedelta(days=5), capacity=2, remaining=1)

        self.future_booking = Booking.objects.create(attraction=self.attraction, slot=self.slot_future, full_name='Bob', email='bob@example.com', user=self.user)
        self.past_booking = Booking.objects.create(attraction=self.attraction, slot=self.slot_past, full_name='BobPast', email='bobpast@example.com', user=self.user)

    def test_owner_can_cancel_future_booking_and_increment_remaining(self):
        """Owner can cancel a future booking and slot.remaining increments (capped).

        Params: authenticated owner, future booking

        Expected: booking.cancelled True and slot.remaining increased by 1 up to capacity.
        Pass: cancelled True and remaining == min(capacity, before+1). Fail: booking not cancelled or remaining incorrect.
        """
        self.client.login(username='bob', password='testpass')
        before = self.slot_future.remaining
        url = reverse('cancel_booking', args=[self.future_booking.pk])
        resp = self.client.post(url, follow=True)
        self.future_booking.refresh_from_db()
        self.slot_future.refresh_from_db()
        self.assertTrue(self.future_booking.cancelled)
        self.assertEqual(self.slot_future.remaining, min(self.slot_future.capacity, before + 1))

    def test_cannot_cancel_past_booking(self):
        """Users cannot cancel bookings whose slot date is in the past.

        Params: authenticated owner, past booking

        Expected: booking.cancelled remains False. Pass: not cancelled. Fail: booking becomes cancelled.
        """
        self.client.login(username='bob', password='testpass')
        url = reverse('cancel_booking', args=[self.past_booking.pk])
        resp = self.client.post(url, follow=True)
        self.past_booking.refresh_from_db()
        self.assertFalse(self.past_booking.cancelled)

    def test_other_user_cannot_cancel(self):
        """Other authenticated users cannot cancel bookings they don't own.

        Params: authenticated non-owner

        Expected: booking remains active (not cancelled). Pass: cancelled False. Fail: another user cancels it.
        """
        self.client.login(username='other', password='testpass')
        url = reverse('cancel_booking', args=[self.future_booking.pk])
        resp = self.client.post(url, follow=True)
        self.future_booking.refresh_from_db()
        self.assertFalse(self.future_booking.cancelled)

    def test_cancel_does_not_increase_remaining_above_capacity(self):
        """Cancelling does not increase VisitSlot.remaining above capacity.

        Setup: set remaining == capacity and cancel a booking.

        Expected: booking.cancelled True and remaining == capacity (not greater). Pass: equality holds.
        """
        # set remaining == capacity
        self.slot_future.capacity = 2
        self.slot_future.remaining = 2
        self.slot_future.save()
        self.assertFalse(self.future_booking.cancelled)
        self.client.login(username='bob', password='testpass')
        url = reverse('cancel_booking', args=[self.future_booking.pk])
        resp = self.client.post(url, follow=True)
        self.future_booking.refresh_from_db()
        self.slot_future.refresh_from_db()
        self.assertTrue(self.future_booking.cancelled)
        self.assertEqual(self.slot_future.remaining, self.slot_future.capacity)


class CancelConcurrencyTests(TransactionTestCase):
    """Ensure concurrent cancellation does not let remaining exceed capacity."""

    def setUp(self):
        self.user = User.objects.create_user(username='concurrent', email='concurrent@example.com', password='pw')
        self.attraction = Attraction.objects.create(name='Concurrent Park', slug='concurrent-park')
        self.slot = VisitSlot.objects.create(attraction=self.attraction, date=timezone.now().date() + timezone.timedelta(days=5), capacity=5, remaining=0)

        self.bookings = []
        for i in range(10):
            # Use different users so we don't violate the (user, slot) active-uniqueness rule.
            u = User.objects.create_user(
                username=f'concurrent{i}',
                email=f'concurrent{i}@example.com',
                password='pw'
            )
            b = Booking.objects.create(user=u, attraction=self.attraction, slot=self.slot, email=f'user{i}@example.com')
            self.bookings.append(b)

        self.start_barrier = threading.Barrier(len(self.bookings))

    def _cancel_worker(self, booking_pk):
        close_old_connections()
        try:
            self.start_barrier.wait()
        except Exception:
            pass
        attempts = 5
        for attempt in range(attempts):
            try:
                with transaction.atomic():
                    b = Booking.objects.select_for_update().get(pk=booking_pk)
                    if not b.cancelled:
                        b.cancelled = True
                        b.save()
                        VisitSlot.objects.filter(pk=self.slot.pk).update(remaining=Least(F('remaining') + 1, F('capacity')))
                break
            except OperationalError:
                if attempt == attempts - 1:
                    raise
                time.sleep(0.01 + random.random() * 0.02)
            finally:
                close_old_connections()

    def test_concurrent_cancels_do_not_exceed_capacity(self):
        """Concurrent cancellations must not let remaining exceed slot.capacity.

        Setup: spawn threads that cancel many bookings concurrently using DB-side capped update.

        Expected: final VisitSlot.remaining == capacity. Pass: equality holds. Fail: remaining > capacity.
        """
        threads = []
        for b in self.bookings:
            t = threading.Thread(target=self._cancel_worker, args=(b.pk,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        s = VisitSlot.objects.get(pk=self.slot.pk)
        self.assertEqual(s.remaining, s.capacity)