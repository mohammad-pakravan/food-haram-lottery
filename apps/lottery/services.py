from django.conf import settings
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta
from .models import Ticket
import random
import requests


class LotteryService:
    """
    Service for lottery operations
    """
    
    @staticmethod
    def get_current_week_start():
        """
        Get the start of current week (Saturday 8 AM Tehran time)
        Returns datetime in UTC (timezone-aware)
        """
        try:
            from zoneinfo import ZoneInfo
            tehran_tz = ZoneInfo('Asia/Tehran')
        except ImportError:
            import pytz
            tehran_tz = pytz.timezone('Asia/Tehran')
        
        now_tehran = timezone.now().astimezone(tehran_tz)
        current_weekday = now_tehran.weekday()
        
        # Calculate start of week (Saturday 8 AM)
        if current_weekday == 5:  # Saturday
            if now_tehran.hour < 8:
                days_to_saturday = 7
            else:
                days_to_saturday = 0
        else:
            days_to_saturday = (current_weekday - 5) % 7
            if days_to_saturday == 0:
                days_to_saturday = 7
        
        saturday_8am = now_tehran.replace(hour=8, minute=0, second=0, microsecond=0)
        saturday_8am = saturday_8am - timedelta(days=days_to_saturday)
        week_start = saturday_8am.astimezone(timezone.utc)
        
        return week_start
    
    @staticmethod
    def get_current_week_tickets():
        """
        Get all pending tickets from current week
        Current week: Saturday 8 AM to Wednesday 8 PM
        """
        week_start = LotteryService.get_current_week_start()
        
        # Get all pending tickets from this week
        tickets = Ticket.objects.filter(
            status='pending',
            created_at__gte=week_start
        )
        
        return tickets
    
    @staticmethod
    def get_current_week_winners():
        """
        Get all winners from current week
        Current week: Saturday 8 AM to Wednesday 8 PM
        """
        week_start = LotteryService.get_current_week_start()
        
        # Get all won tickets from this week
        winners = Ticket.objects.filter(
            status='won',
            created_at__gte=week_start
        ).select_related('user').order_by('-created_at')
        
        return winners
    
    @staticmethod
    def get_user_previous_info(user):
        """
        Get user's previous completed ticket information
        Returns: dict with full_name, national_id if found, None otherwise
        Finds the most recent ticket that has completed information (not cancelled)
        """
        # Find the most recent completed ticket for this user
        # Exclude cancelled tickets as they might be incomplete
        previous_ticket = Ticket.objects.filter(
            user=user,
            full_name__isnull=False,
            national_id__isnull=False
        ).exclude(
            Q(full_name='') | Q(national_id='') | Q(status='cancelled')
        ).order_by('-created_at').first()
        
        if previous_ticket:
            return {
                'full_name': previous_ticket.full_name,
                'national_id': previous_ticket.national_id
            }
        return None
    
    @staticmethod
    def select_winners(count=None):
        """
        Select random winners from current week's pending tickets
        If user has previous completed information, it will be copied automatically
        """
        if count is None:
            count = settings.LOTTERY_WINNERS_COUNT
        
        tickets = LotteryService.get_current_week_tickets()
        tickets_list = list(tickets)
        
        if len(tickets_list) < count:
            count = len(tickets_list)
        
        # Select random winners
        winners = random.sample(tickets_list, count)
        
        # Update status to 'won' and copy previous info if available
        winner_ids = [ticket.id for ticket in winners]
        
        # Update each winner ticket with previous info if available
        # Also set default values: received_date = "پنجشنبه", selected_period = "ناهار"
        for ticket in winners:
            previous_info = LotteryService.get_user_previous_info(ticket.user)
            update_data = {
                'status': 'won',
                'received_date': 'پنجشنبه',
                'selected_period': 'ناهار'
            }
            
            if previous_info:
                # Copy previous information (full_name and national_id)
                update_data['full_name'] = previous_info['full_name']
                update_data['national_id'] = previous_info['national_id']
            
            Ticket.objects.filter(id=ticket.id).update(**update_data)
        
        # Refresh winners to get updated status
        winners = Ticket.objects.filter(id__in=winner_ids)
        
        return winners
    
    @staticmethod
    def send_winner_sms(ticket):
        """
        Send SMS to winner using KavehNegar
        """
        from apps.accounts.services import KavehNegarService
        
        phone_number = ticket.user.phone_number
        ticket_number = ticket.ticket_number
        template = settings.LOTTERY_WINNER_SMS_TEMPLATE
        
        if not template:
            raise ValueError("LOTTERY_WINNER_SMS_TEMPLATE is not configured")
        
        # Send SMS with ticket number as token
        try:
            KavehNegarService.send_otp_sms(phone_number, ticket_number, template)
            return True
        except Exception as e:
            # Log error but don't fail the lottery
            if settings.DEBUG:
                print(f"Failed to send SMS to {phone_number}: {str(e)}")
            return False


class KavehNegarLotteryService:
    """
    Service for sending lottery winner SMS via KavehNegar
    """
    
    @staticmethod
    def send_winner_sms(phone_number, ticket_number, template_name=None):
        """
        Send winner SMS via KavehNegar API
        """
        api_key = settings.KAVEHNEGAR_API_KEY
        template = template_name or settings.LOTTERY_WINNER_SMS_TEMPLATE
        
        if not api_key:
            raise ValueError("KAVEHNEGAR_API_KEY is not configured")
        
        if not template:
            raise ValueError("LOTTERY_WINNER_SMS_TEMPLATE is not configured")
        
        url = f"{settings.KAVEHNEGAR_API_URL}/{api_key}/verify/lookup.json"
        
        data = {
            'template': template,
            'receptor': phone_number,
            'token': ticket_number
        }
        
        try:
            response = requests.post(url, data=data, timeout=10)
            
            if response.status_code != 200:
                error_msg = f"KavehNegar API returned status {response.status_code}"
                try:
                    error_data = response.json()
                    error_message = error_data.get('return', {}).get('message', 'Unknown error')
                    error_status = error_data.get('return', {}).get('status', response.status_code)
                    error_msg = f"KavehNegar API error (status {error_status}): {error_message}"
                except:
                    error_msg += f": {response.text}"
                raise Exception(error_msg)
            
            result = response.json()
            return_status = result.get('return', {}).get('status')
            
            if return_status == 200:
                return True
            else:
                error_message = result.get('return', {}).get('message', 'Unknown error')
                raise Exception(f"KavehNegar API error: {error_message}")
                
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to send SMS via KavehNegar: {str(e)}")

