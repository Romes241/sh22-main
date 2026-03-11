from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore
from django_apscheduler.models import DjangoJobExecution
from django.utils import timezone
from django.conf import settings
import datetime
from django.db.models import F
import logging
from .models import TicketDraw, TicketDrawVisitSlot, Attraction, VisitSlot, Booking, TicketDrawBooking, FeedbackEmailTemplate, EmailTemplate
from .views import assign_next_winner, send_attraction_booking_email_reminder, send_draw_booking_email_reminder, send_attraction_booking_email_ticket_distribution, send_feedback_email_request

logger = logging.getLogger(__name__)

def send_attraction_ticket():
    # send tickets 3 days before the users attraction
    now = timezone.now()

    eligible_bookings = Booking.objects.filter(cancelled=False,ticket_sent=False,attraction__cancel_deadline__isnull=False,attraction__cancel_deadline__lte=now).select_related('user', 'attraction', 'slot')

    for booking in eligible_bookings:
        send_attraction_booking_email_ticket_distribution(booking)
        booking.ticket_sent = True
        booking.save(update_fields=['ticket_sent'])


def check_expired_winners():
    
    now = timezone.now()
    
    # Get all draws with winners selected
    draws = TicketDraw.objects.filter(winner_booking__isnull=False,winner_selected_at__isnull=False).select_related('winner_booking')
    
    
    
    for draw in draws:
        winner = draw.winner_booking
        
        if winner.is_accepted or winner.cancelled:
            continue
            
        # Check if 72 hours have passed
        deadline = draw.winner_selected_at + datetime.timedelta(hours=72)
        if now > deadline:
            
            
            winner.cancelled = True
            winner.save(update_fields=["cancelled"])
            
            
            TicketDrawVisitSlot.objects.filter(pk=winner.slot_id).update(remaining=F("remaining") + winner.num_tickets)
            
            draw.winner_booking = None
            draw.winner_selected_at = None
            draw.save(update_fields=["winner_booking", "winner_selected_at"])
            
            # Select new winner
            assign_next_winner(draw)
            

def send_reminders():
    # checks reminders and send one for booking and ticket draw one day before their slot
    today = timezone.now().date()
    tomorrow = today + datetime.timedelta(days=1)


    attractions = Booking.objects.filter(slot__date=tomorrow,cancelled=False).select_related('user', 'attraction', 'slot')

    for attraction_booking in attractions:
        send_attraction_booking_email_reminder(attraction_booking)


    ticketdraws = Booking.objects.filter(slot__date=tomorrow,cancelled=False).select_related('user', 'ticket_draw', 'slot')

    for draw_booking in ticketdraws:
        send_draw_booking_email_reminder(draw_booking)


def send_scheduled_feedback_emails():
    """Send feedback emails to users whose attraction visit has already passed.
    Runs daily. Respects the enabled flag on FeedbackEmailTemplate.
    """
    template = FeedbackEmailTemplate.get_template()

    if not template.enabled:
        logger.info("Feedback emails are disabled – skipping scheduled send.")
        return

    feedback_et = (
        EmailTemplate.objects.filter(type="feedback", is_default=True).first()
        or EmailTemplate.objects.filter(type="feedback").first()
    )
    if feedback_et is None:
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
        feedback_email_sent=False,
        slot__date__lt=now.date(),
    ).select_related("slot", "attraction", "user")

    sent_count = 0
    for booking in completed_bookings:
        if booking.slot.time:
            slot_dt = timezone.make_aware(
                datetime.datetime.combine(booking.slot.date, booking.slot.time)
            )
            if booking.attraction.duration_minutes:
                slot_dt += datetime.timedelta(minutes=booking.attraction.duration_minutes)
            if now < slot_dt:
                continue
        try:
            send_feedback_email_request(booking, template.feedback_url)
            booking.feedback_email_sent = True
            booking.save(update_fields=["feedback_email_sent"])
            sent_count += 1
        except Exception as e:
            logger.error(f"Failed to send feedback email for booking #{booking.id}: {e}")

    logger.info(f"Feedback email job: sent {sent_count} email(s).")


def cleanup_old_jobs():
    try:
        # Delete job executions older than 30 days
        DjangoJobExecution.objects.delete_old_job_executions(30)
        logger.info("Cleaned up old job executions")
    except Exception as e:
        logger.error(f"Failed to clean up old jobs: {e}")
    


def start_scheduler():
    scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE)
    scheduler.add_jobstore(DjangoJobStore(), "default")

    scheduler.add_job(
        send_attraction_ticket,
        trigger="interval",
        hours=1,
        id="send_attraction_ticket",
        replace_existing=True,
        misfire_grace_time=120,
    )
    
    # Check every hour for expired winners
    scheduler.add_job(
        check_expired_winners,
        trigger="interval",
        hours=1,
        id="check_expired_winners",
        replace_existing=True,
        misfire_grace_time=120,
    )

    # Send reminders every day at 8:00 AM
    scheduler.add_job(
        send_reminders,
        trigger="cron",
        hour=8,
        minute=0,
        id="send_reminders",
        replace_existing=True,
        misfire_grace_time=3600,  # 1 hour grace time
    )
        
    # Clean up old job executions every day at 3:00 AM
    scheduler.add_job(
        cleanup_old_jobs,
        trigger="cron",
        hour=3,
        minute=0,
        id="cleanup_old_jobs",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # Send feedback emails every day at 10:00 AM
    scheduler.add_job(
        send_scheduled_feedback_emails,
        trigger="cron",
        hour=10,
        minute=0,
        id="send_feedback_emails",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    scheduler.start()