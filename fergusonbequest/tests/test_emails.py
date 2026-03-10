"""Critical-path tests for email templates, sending, and admin management."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core import mail
from django.db import IntegrityError
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from fergusonbequest.models import (
    Attraction,
    Booking,
    EmailTemplate,
    TicketDraw,
    TicketDrawBooking,
    TicketDrawVisitSlot,
    VisitSlot,
)
from fergusonbequest.views import (
    get_email_context,
    send_attraction_booking_email_confirmation,
    send_draw_booking_email_confirmation,
    send_template_email,
)

User = get_user_model()


class EmailTemplateCriticalTests(TestCase):
    def test_unique_default_per_type_constraint(self):
        """
        Parameters: None.
        Expected Output: Creating a second default template for same type raises IntegrityError.
        Pass: IntegrityError is raised.
        Fail: Second default template is saved.
        """
        EmailTemplate.objects.create(
            type="attraction_confirmation",
            name="Default A",
            subject="A",
            body="A",
            is_default=True,
        )

        with self.assertRaises(IntegrityError):
            EmailTemplate.objects.create(
                type="attraction_confirmation",
                name="Default B",
                subject="B",
                body="B",
                is_default=True,
            )


class EmailSendingCriticalTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="pass12345",
            first_name="John",
            last_name="Doe",
        )
        self.attraction = Attraction.objects.create(
            name="Edinburgh Zoo",
            slug="edinburgh-zoo",
            location="Edinburgh",
            description="Zoo",
        )
        self.slot = VisitSlot.objects.create(
            attraction=self.attraction,
            date=timezone.now().date() + timedelta(days=5),
            time=timezone.now().time(),
            capacity=20,
            remaining=20,
        )
        self.booking = Booking.objects.create(
            user=self.user,
            attraction=self.attraction,
            slot=self.slot,
            full_name="John Doe",
            email=self.user.email,
            num_tickets=2,
            agreed_terms=True,
        )

    def test_send_template_email_renders_and_sends(self):
        """
        Parameters: template_type, recipient, context dict.
        Expected Output: One rendered email is sent.
        Pass: outbox length is 1 and rendered subject/body contain booking/user values.
        Fail: no email sent or placeholders not rendered.
        """
        EmailTemplate.objects.create(
            type="attraction_confirmation",
            name="Booking",
            subject="Booking for {{ attraction_name }}",
            body="Hi {{ first_name }}",
            is_default=True,
        )
        context = get_email_context(booking=self.booking)

        send_template_email("attraction_confirmation", "recipient@example.com", context)

        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertEqual(sent.to, ["recipient@example.com"])
        self.assertIn("Edinburgh Zoo", sent.subject)
        self.assertIn("Hi John", sent.body)
        self.assertEqual(len(sent.alternatives), 1)

    def test_send_template_email_no_template_sends_nothing(self):
        """
        Parameters: template_type with no DB template.
        Expected Output: Function exits safely with no email sent.
        Pass: outbox remains empty.
        Fail: email is sent or exception is raised.
        """
        context = get_email_context(user=self.user)
        send_template_email("attraction_confirmation", "recipient@example.com", context)
        self.assertEqual(len(mail.outbox), 0)

    def test_wrapper_functions_send_to_booking_users(self):
        """
        Parameters: booking and draw_booking objects.
        Expected Output: Wrapper functions send one email each to object user email.
        Pass: outbox has 2 emails and recipients match booking users.
        Fail: wrong count or recipient mismatch.
        """
        EmailTemplate.objects.create(
            type="attraction_confirmation",
            name="Attraction Default",
            subject="Attraction {{ attraction_name }}",
            body="Hello {{ first_name }}",
            is_default=True,
        )
        EmailTemplate.objects.create(
            type="draw_confirmation",
            name="Draw Default",
            subject="Draw {{ draw_name }}",
            body="Hello {{ first_name }}",
            is_default=True,
        )

        draw = TicketDraw.objects.create(
            name="Special Exhibition",
            slug="special-exhibition",
            location="London",
            description="Desc",
            draw_date=timezone.now() + timedelta(days=10),
        )
        draw_slot = TicketDrawVisitSlot.objects.create(
            ticket_draw=draw,
            date=timezone.now().date() + timedelta(days=12),
            time=timezone.now().time(),
            capacity=10,
            remaining=10,
        )
        draw_booking = TicketDrawBooking.objects.create(
            user=self.user,
            ticket_draw=draw,
            slot=draw_slot,
            full_name="John Doe",
            email=self.user.email,
            num_tickets=1,
            agreed_terms=True,
        )

        send_attraction_booking_email_confirmation(self.booking)
        send_draw_booking_email_confirmation(draw_booking)

        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[0].to, [self.user.email])
        self.assertEqual(mail.outbox[1].to, [self.user.email])


class AdminEmailCriticalTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.staff = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="pass12345",
            is_staff=True,
        )
        self.regular = User.objects.create_user(
            username="user",
            email="user@example.com",
            password="pass12345",
        )
        self.template = EmailTemplate.objects.create(
            type="attraction_confirmation",
            name="Template A",
            subject="A",
            body="A",
            is_default=True,
        )

    def test_admin_email_requires_staff(self):
        """
        Parameters: unauthenticated and non-staff requests.
        Expected Output: access denied via redirect.
        Pass: both requests return 302.
        Fail: non-staff gets 200 access.
        """
        self.assertEqual(self.client.get(reverse("admin_email")).status_code, 302)
        self.client.login(username="user", password="pass12345")
        self.assertEqual(self.client.get(reverse("admin_email")).status_code, 302)

    def test_admin_can_create_and_update_template(self):
        """
        Parameters: staff POST create and save actions.
        Expected Output: new template created, selected template updated.
        Pass: new template exists and subject/body are updated.
        Fail: create/save does not persist changes.
        """
        self.client.login(username="staff", password="pass12345")

        create_response = self.client.post(
            reverse("admin_email") + "?email_type=draw_confirmation",
            {"create": "1"},
        )
        self.assertEqual(create_response.status_code, 302)
        self.assertTrue(EmailTemplate.objects.filter(type="draw_confirmation").exists())

        save_response = self.client.post(
            reverse("admin_email")
            + f"?email_type=attraction_confirmation&template_id={self.template.id}",
            {"save": "1", "subject": "Updated", "body": "Updated body"},
        )
        self.assertEqual(save_response.status_code, 200)
        self.template.refresh_from_db()
        self.assertEqual(self.template.subject, "Updated")
        self.assertEqual(self.template.body, "Updated body")

    def test_deleting_default_assigns_new_default(self):
        """
        Parameters: staff delete action on default template.
        Expected Output: deleted default replaced by another template of same type.
        Pass: remaining template is marked default.
        Fail: no default remains after deletion.
        """
        self.client.login(username="staff", password="pass12345")
        replacement = EmailTemplate.objects.create(
            type="attraction_confirmation",
            name="Template B",
            subject="B",
            body="B",
            is_default=False,
        )

        delete_response = self.client.post(
            reverse("admin_email")
            + f"?email_type=attraction_confirmation&template_id={self.template.id}",
            {"delete": "1", "subject": self.template.subject, "body": self.template.body},
        )
        self.assertEqual(delete_response.status_code, 302)

        replacement.refresh_from_db()
        self.assertTrue(replacement.is_default)
