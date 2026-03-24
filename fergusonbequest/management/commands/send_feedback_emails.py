from django.core.management.base import BaseCommand
from django.utils import timezone
from fergusonbequest.models import Booking, FeedbackEmailTemplate, EmailTemplate, BookingFeedback
from fergusonbequest.views import send_feedback_email_request
from datetime import timedelta


class Command(BaseCommand):
    help = 'Send feedback emails to users after their attraction visit has passed'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show which emails would be sent without actually sending them',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Resend emails even if already sent (for testing)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']
        
        # Get the email template
        template = FeedbackEmailTemplate.get_template()
        
        # Check if feedback emails are enabled
        if not template.enabled:
            self.stdout.write(
                self.style.WARNING('Feedback emails are currently disabled in admin settings.')
            )
            return
        
        feedback_email_template = (
            EmailTemplate.objects.filter(type="feedback", is_default=True).first()
            or EmailTemplate.objects.filter(type="feedback").first()
        )

        if feedback_email_template is None:
            EmailTemplate.objects.create(
                type="feedback",
                name="Feedback Template",
                subject=template.subject,
                body=template.body,
                is_default=True,
            )

        now = timezone.now()
        
        completed_bookings = Booking.objects.filter(
            cancelled=False,
            slot__date__lte=now.date()
        ).select_related('slot', 'attraction', 'user')
        
        initial_bookings = []
        reminder_bookings = []

        for booking in completed_bookings:
            slot_time = booking.slot.time or timezone.datetime.max.time().replace(microsecond=0)
            slot_datetime = timezone.make_aware(
                timezone.datetime.combine(booking.slot.date, slot_time)
            )
            if booking.attraction.duration_minutes:
                slot_datetime += timedelta(minutes=booking.attraction.duration_minutes)

            if now < slot_datetime:
                continue

            expiry_deadline = slot_datetime + timedelta(days=template.expiry_days)
            if now > expiry_deadline:
                continue

            if BookingFeedback.objects.filter(booking_id=booking.id).exists():
                continue

            if force:
                initial_bookings.append(booking)
                continue

            if not booking.feedback_email_sent:
                initial_bookings.append(booking)
                continue

            if (
                template.reminder_enabled
                and not booking.feedback_reminder_sent
                and booking.feedback_email_sent_at
                and now >= booking.feedback_email_sent_at + timedelta(days=template.reminder_delay_days)
            ):
                reminder_bookings.append(booking)

        if not initial_bookings and not reminder_bookings:
            self.stdout.write(self.style.SUCCESS('No eligible bookings found for feedback emails.'))
            return

        self.stdout.write(
            f'Found {len(initial_bookings)} initial email(s) and {len(reminder_bookings)} reminder(s) eligible.'
        )
        
        sent_count = 0
        error_count = 0
        
        for booking in initial_bookings:
            if dry_run:
                self.stdout.write(
                    f'[DRY RUN] Would send feedback email to {booking.email} for booking #{booking.id}'
                )
                sent_count += 1
            else:
                try:
                    send_feedback_email_request(booking, template.feedback_url, template=template)
                    
                    booking.feedback_email_sent = True
                    booking.feedback_email_sent_at = now
                    booking.save(update_fields=['feedback_email_sent', 'feedback_email_sent_at'])
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'Sent feedback email to {booking.email} for booking #{booking.id}')
                    )
                    sent_count += 1
                    
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'Failed to send email to {booking.email}: {str(e)}')
                    )
                    error_count += 1

        for booking in reminder_bookings:
            if dry_run:
                self.stdout.write(
                    f'[DRY RUN] Would send feedback reminder to {booking.email} for booking #{booking.id}'
                )
                sent_count += 1
                continue

            try:
                send_feedback_email_request(booking, template.feedback_url, template=template)

                booking.feedback_reminder_sent = True
                booking.feedback_reminder_sent_at = now
                booking.save(update_fields=['feedback_reminder_sent', 'feedback_reminder_sent_at'])

                self.stdout.write(
                    self.style.SUCCESS(f'Sent feedback reminder to {booking.email} for booking #{booking.id}')
                )
                sent_count += 1
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Failed to send reminder to {booking.email}: {str(e)}')
                )
                error_count += 1

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(f'\n[DRY RUN] Would have sent {sent_count} feedback email(s).')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'\nSuccessfully sent {sent_count} feedback email(s).')
            )
            if error_count > 0:
                self.stdout.write(
                    self.style.WARNING(f'Failed to send {error_count} email(s).')
                )
