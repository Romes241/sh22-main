from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore
from django_apscheduler.models import DjangoJobExecution
from django.utils import timezone
from django.conf import settings
import datetime
from django.db.models import F
import logging

logger = logging.getLogger(__name__)


def check_expired_winners():
    from .models import TicketDraw, TicketDrawVisitSlot
    from .views import assign_next_winner
    
    now = timezone.now()
    
    # Get all draws with winners selected
    draws = TicketDraw.objects.filter(winner_booking__isnull=False,winner_selected_at__isnull=False).select_related('winner_booking')
    
    redrawn_count = 0
    
    for draw in draws:
        winner = draw.winner_booking
        
        if winner.is_accepted or winner.cancelled:
            continue
            
        # Check if 72 hours have passed
        deadline = draw.winner_selected_at + datetime.timedelta(hours=72)
        if now > deadline:
            logger.info(f"Winner {winner.id} for draw {draw.name} has expired")
            
            
            winner.cancelled = True
            winner.save(update_fields=["cancelled"])
            
            
            TicketDrawVisitSlot.objects.filter(pk=winner.slot_id).update(remaining=F("remaining") + winner.num_tickets)
            
            draw.winner_booking = None
            draw.winner_selected_at = None
            draw.save(update_fields=["winner_booking", "winner_selected_at"])
            
            # Select new winner
            assign_next_winner(draw)
            
            redrawn_count += 1
    


def start_scheduler():
    scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE)
    scheduler.add_jobstore(DjangoJobStore(), "default")
    
    # Check every hour for expired winners
    scheduler.add_job(
        check_expired_winners,
        trigger="interval",
        hours=1,
        id="check_expired_winners",
        replace_existing=True,
        misfire_grace_time=120,
    )
    
    scheduler.start()