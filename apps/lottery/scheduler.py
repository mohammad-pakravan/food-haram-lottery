"""
Scheduler for automatic lottery execution
Runs every Wednesday at 8 PM Tehran time
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
try:
    from zoneinfo import ZoneInfo
except ImportError:
    import pytz
from django.conf import settings
from django.utils import timezone
from django_apscheduler.jobstores import DjangoJobStore, register_events
from django_apscheduler.models import DjangoJobExecution
import logging

logger = logging.getLogger(__name__)


def run_lottery_job():
    """
    Job function to run lottery
    This will be called automatically every Wednesday at 8 PM Tehran time
    """
    from apps.lottery.services import LotteryService, KavehNegarLotteryService
    
    try:
        logger.info("Starting automatic lottery execution...")
        
        # Get tickets for current week
        tickets = LotteryService.get_current_week_tickets()
        tickets_count = tickets.count()
        
        if tickets_count == 0:
            logger.warning("No pending tickets found for current week")
            return
        
        # Select winners
        winners = LotteryService.select_winners()
        winner_count = winners.count()
        
        logger.info(f"Selected {winner_count} winners")
        
        # Send SMS to winners
        success_count = 0
        fail_count = 0
        
        for winner in winners:
            try:
                KavehNegarLotteryService.send_winner_sms(
                    winner.user.phone_number,
                    winner.ticket_number
                )
                success_count += 1
                logger.info(f"SMS sent to {winner.user.phone_number} (Ticket: {winner.ticket_number})")
            except Exception as e:
                fail_count += 1
                logger.error(f"Failed to send SMS to {winner.user.phone_number}: {str(e)}")
        
        logger.info(f"Lottery completed! Winners: {winner_count}, SMS sent: {success_count}, Failed: {fail_count}")
        
    except Exception as e:
        logger.error(f"Error in lottery execution: {str(e)}")


def cancel_incomplete_winners():
    """
    Cancel tickets of winners who didn't complete their info by Thursday 8 AM
    This runs every Thursday at 8 AM Tehran time
    """
    from apps.lottery.models import Ticket
    from datetime import timedelta
    from django.utils import timezone
    
    try:
        from zoneinfo import ZoneInfo
        tehran_tz = ZoneInfo('Asia/Tehran')
    except ImportError:
        import pytz
        tehran_tz = pytz.timezone('Asia/Tehran')
    
    now_tehran = timezone.now().astimezone(tehran_tz)
    
    # Get all won tickets
    won_tickets = Ticket.objects.filter(status='won')
    
    cancelled_count = 0
    
    for ticket in won_tickets:
        # Calculate deadline for this specific ticket
        # Deadline is Thursday 8 AM after the ticket was created (Wednesday 8 PM)
        ticket_created_tehran = ticket.created_at.astimezone(tehran_tz)
        ticket_weekday = ticket_created_tehran.weekday()
        
        # Find the Thursday 8 AM after ticket creation
        if ticket_weekday == 2:  # Wednesday (lottery day)
            # Deadline is next day (Thursday) 8 AM
            days_to_thursday = 1
        else:
            # Calculate days to next Thursday
            days_to_thursday = (3 - ticket_weekday) % 7
            if days_to_thursday == 0:
                days_to_thursday = 7
        
        deadline = ticket_created_tehran.replace(hour=8, minute=0, second=0, microsecond=0)
        deadline = deadline + timedelta(days=days_to_thursday)
        
        # Check if deadline has passed and ticket is incomplete
        if now_tehran >= deadline:
            # Check if ticket is incomplete (any required field is missing)
            is_incomplete = (
                not ticket.full_name or
                not ticket.national_id or
                not ticket.received_date or
                not ticket.selected_period or
                ticket.quantity is None
            )
            
            if is_incomplete:
                ticket.status = 'cancelled'
                ticket.save()
                cancelled_count += 1
                logger.info(f"Cancelled incomplete ticket {ticket.ticket_number} (User: {ticket.user.phone_number})")
    
    logger.info(f"Cancelled {cancelled_count} incomplete winner tickets")
    
    return cancelled_count


def start_scheduler():
    """
    Start the scheduler for automatic lottery execution
    """
    try:
        from zoneinfo import ZoneInfo
        tehran_tz = ZoneInfo('Asia/Tehran')
    except ImportError:
        import pytz
        tehran_tz = pytz.timezone('Asia/Tehran')
    
    scheduler = BackgroundScheduler(timezone=tehran_tz)
    scheduler.add_jobstore(DjangoJobStore(), "default")
    
    # Schedule lottery to run every Wednesday at 8 PM Tehran time
    scheduler.add_job(
        run_lottery_job,
        trigger=CronTrigger(day_of_week='wed', hour=20, minute=0, timezone=tehran_tz),
        id='lottery_job',
        name='Run Lottery Every Wednesday 8 PM',
        replace_existing=True,
    )
    
    # Schedule cancellation job to run every Thursday at 8 AM Tehran time
    scheduler.add_job(
        cancel_incomplete_winners,
        trigger=CronTrigger(day_of_week='thu', hour=8, minute=0, timezone=tehran_tz),
        id='cancel_incomplete_winners_job',
        name='Cancel Incomplete Winners Every Thursday 8 AM',
        replace_existing=True,
    )
    
    register_events(scheduler)
    
    scheduler.start()
    logger.info("Lottery scheduler started. Will run every Wednesday at 8 PM Tehran time.")
    logger.info("Cancellation job scheduled. Will run every Thursday at 8 AM Tehran time.")
