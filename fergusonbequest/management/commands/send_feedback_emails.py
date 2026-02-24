from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.db.models import Q
from fergusonbequest.models import Booking, FeedbackEmailTemplate
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
        
        now = timezone.now()
        
        completed_bookings = Booking.objects.filter(
            cancelled=False,
            slot__date__lt=now.date()
        ).select_related('slot', 'attraction', 'user')
        
        eligible_bookings = []
        for booking in completed_bookings:

            if not force and booking.feedback_email_sent:
                continue

            if booking.slot.time:
                slot_datetime = timezone.make_aware(
                    timezone.datetime.combine(booking.slot.date, booking.slot.time)
                )
                if booking.attraction.duration_minutes:
                    slot_datetime += timedelta(minutes=booking.attraction.duration_minutes)
                
                if now >= slot_datetime:
                    eligible_bookings.append(booking)
            else:

                eligible_bookings.append(booking)
        
        if not eligible_bookings:
            self.stdout.write(self.style.SUCCESS('No eligible bookings found for feedback emails.'))
            return
        
        self.stdout.write(f'Found {len(eligible_bookings)} booking(s) eligible for feedback emails.')
        
        sent_count = 0
        error_count = 0
        
        for booking in eligible_bookings:
            user_name = booking.user.first_name if booking.user and booking.user.first_name else booking.full_name.split()[0]

            subject = template.subject.format(
                attraction_name=booking.attraction.name,
                user_name=user_name,
                visit_date=booking.slot.date.strftime('%d %B %Y'),
                feedback_url=template.feedback_url
            )
            
            message = template.body.format(
                user_name=user_name,
                attraction_name=booking.attraction.name,
                visit_date=booking.slot.date.strftime('%d %B %Y'),
                feedback_url=template.feedback_url
            )
            
            if dry_run:
                self.stdout.write(
                    f'[DRY RUN] Would send feedback email to {booking.email} for booking #{booking.id}'
                )
                sent_count += 1
            else:
                try:
                    send_mail(
                        subject=subject,
                        message=message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[booking.email],
                        fail_silently=False,
                    )
                    
                    booking.feedback_email_sent = True
                    booking.save(update_fields=['feedback_email_sent'])
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'Sent feedback email to {booking.email} for booking #{booking.id}')
                    )
                    sent_count += 1
                    
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'Failed to send email to {booking.email}: {str(e)}')
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
