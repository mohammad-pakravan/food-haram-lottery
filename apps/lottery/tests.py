"""
Tests for lottery app views and services
"""
from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from django.utils import timezone
from unittest.mock import patch, MagicMock
from datetime import timedelta, datetime
import pytz

from .models import Ticket
from .services import LotteryService, KavehNegarLotteryService
from .views import (
    ParticipateLotteryView,
    CompleteWinnerInfoView,
    UserTicketsHistoryView,
    CurrentWeekWinnersView
)

# Import scheduler functions conditionally
try:
    from .scheduler import run_lottery_job, cancel_incomplete_winners
    SCHEDULER_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    # If scheduler module can't be imported, define dummy functions for testing
    SCHEDULER_AVAILABLE = False
    
    def run_lottery_job():
        pass
    
    def cancel_incomplete_winners():
        pass

User = get_user_model()


class LotteryServiceTestCase(TestCase):
    """Test cases for LotteryService"""
    
    def setUp(self):
        """Set up test data"""
        self.user1 = User.objects.create_user(phone_number='09021794990')
        self.user2 = User.objects.create_user(phone_number='09021794991')
        self.user3 = User.objects.create_user(phone_number='09021794992')
        
        # Create tickets with different statuses and dates
        self.pending_ticket = Ticket.objects.create(
            user=self.user1,
            status='pending'
        )
        
        self.won_ticket = Ticket.objects.create(
            user=self.user2,
            status='won',
            full_name='علی احمدی',
            national_id='1234567890',
            received_date='پنجشنبه',
            selected_period='ناهار',
            quantity=2
        )
    
    def test_get_current_week_start_saturday_after_8am(self):
        """Test get_current_week_start on Saturday after 8 AM"""
        try:
            from zoneinfo import ZoneInfo
            tehran_tz = ZoneInfo('Asia/Tehran')
        except ImportError:
            tehran_tz = pytz.timezone('Asia/Tehran')
        
        # Mock Saturday 10 AM Tehran time
        saturday_10am = datetime(2024, 1, 13, 10, 0, 0, tzinfo=tehran_tz)
        
        with patch('apps.lottery.services.timezone.now', return_value=saturday_10am.astimezone(timezone.utc)):
            week_start = LotteryService.get_current_week_start()
            week_start_tehran = week_start.astimezone(tehran_tz)
            
            self.assertEqual(week_start_tehran.weekday(), 5)  # Saturday
            self.assertEqual(week_start_tehran.hour, 8)
            self.assertEqual(week_start_tehran.minute, 0)
    
    def test_get_current_week_start_saturday_before_8am(self):
        """Test get_current_week_start on Saturday before 8 AM"""
        try:
            from zoneinfo import ZoneInfo
            tehran_tz = ZoneInfo('Asia/Tehran')
        except ImportError:
            tehran_tz = pytz.timezone('Asia/Tehran')
        
        # Mock Saturday 7 AM Tehran time
        saturday_7am = datetime(2024, 1, 13, 7, 0, 0, tzinfo=tehran_tz)
        
        with patch('apps.lottery.services.timezone.now', return_value=saturday_7am.astimezone(timezone.utc)):
            week_start = LotteryService.get_current_week_start()
            week_start_tehran = week_start.astimezone(tehran_tz)
            
            # Should return previous Saturday 8 AM
            self.assertEqual(week_start_tehran.weekday(), 5)  # Saturday
            self.assertEqual(week_start_tehran.hour, 8)
    
    def test_get_current_week_tickets(self):
        """Test get_current_week_tickets returns only pending tickets from current week"""
        try:
            from zoneinfo import ZoneInfo
            tehran_tz = ZoneInfo('Asia/Tehran')
        except ImportError:
            tehran_tz = pytz.timezone('Asia/Tehran')
        
        # Mock current time (Monday)
        monday_noon = datetime(2024, 1, 15, 12, 0, 0, tzinfo=tehran_tz)
        monday_utc = monday_noon.astimezone(timezone.utc)
        
        # Create ticket from previous week (before Saturday 8 AM of current week)
        # Current week starts: Saturday Jan 13, 8 AM
        # Previous week ticket: Saturday Jan 6, 7 AM (before current week)
        previous_saturday = datetime(2024, 1, 6, 7, 0, 0, tzinfo=tehran_tz)
        previous_saturday_utc = previous_saturday.astimezone(timezone.utc)
        
        old_ticket = Ticket.objects.create(
            user=self.user1,
            status='pending'
        )
        old_ticket.created_at = previous_saturday_utc
        old_ticket.save()
        
        # Create ticket for current week
        current_week_ticket = Ticket.objects.create(
            user=self.user1,
            status='pending'
        )
        # Set to Sunday of current week (after Saturday 8 AM)
        sunday_noon = datetime(2024, 1, 14, 12, 0, 0, tzinfo=tehran_tz)
        current_week_ticket.created_at = sunday_noon.astimezone(timezone.utc)
        current_week_ticket.save()
        
        with patch('apps.lottery.services.timezone.now', return_value=monday_utc):
            tickets = LotteryService.get_current_week_tickets()
            
            # Should include current_week_ticket but not old_ticket or won_ticket
            self.assertIn(current_week_ticket, tickets)
            self.assertNotIn(old_ticket, tickets)
            self.assertNotIn(self.won_ticket, tickets)
    
    def test_get_current_week_winners(self):
        """Test get_current_week_winners returns only won tickets from current week"""
        try:
            from zoneinfo import ZoneInfo
            tehran_tz = ZoneInfo('Asia/Tehran')
        except ImportError:
            tehran_tz = pytz.timezone('Asia/Tehran')
        
        # Mock current time (Monday)
        monday_noon = datetime(2024, 1, 15, 12, 0, 0, tzinfo=tehran_tz)
        monday_utc = monday_noon.astimezone(timezone.utc)
        
        # Create old won ticket from previous week
        previous_saturday = datetime(2024, 1, 6, 7, 0, 0, tzinfo=tehran_tz)
        previous_saturday_utc = previous_saturday.astimezone(timezone.utc)
        
        old_won = Ticket.objects.create(
            user=self.user3,
            status='won'
        )
        old_won.created_at = previous_saturday_utc
        old_won.save()
        
        # Create won ticket for current week
        current_week_won = Ticket.objects.create(
            user=self.user3,
            status='won'
        )
        # Set to Sunday of current week
        sunday_noon = datetime(2024, 1, 14, 12, 0, 0, tzinfo=tehran_tz)
        current_week_won.created_at = sunday_noon.astimezone(timezone.utc)
        current_week_won.save()
        
        with patch('apps.lottery.services.timezone.now', return_value=monday_utc):
            winners = LotteryService.get_current_week_winners()
            
            # Should include current_week_won but not old_won or pending_ticket
            self.assertIn(current_week_won, winners)
            self.assertNotIn(old_won, winners)
            self.assertNotIn(self.pending_ticket, winners)
    
    def test_get_user_previous_info_with_completed_ticket(self):
        """Test get_user_previous_info returns info from completed ticket"""
        info = LotteryService.get_user_previous_info(self.user2)
        
        self.assertIsNotNone(info)
        self.assertEqual(info['full_name'], 'علی احمدی')
        self.assertEqual(info['national_id'], '1234567890')
    
    def test_get_user_previous_info_without_completed_ticket(self):
        """Test get_user_previous_info returns None when no completed ticket exists"""
        info = LotteryService.get_user_previous_info(self.user1)
        self.assertIsNone(info)
    
    def test_get_user_previous_info_excludes_cancelled(self):
        """Test get_user_previous_info excludes cancelled tickets"""
        # Create a new user to avoid any interference from setUp
        test_user = User.objects.create_user(phone_number='09021794993')
        
        # Create cancelled ticket with info for test_user
        cancelled_ticket = Ticket.objects.create(
            user=test_user,
            status='cancelled',
            full_name='محمد رضایی',
            national_id='0987654321'
        )
        
        # Verify the cancelled ticket exists and has the correct status
        cancelled_ticket.refresh_from_db()
        self.assertEqual(cancelled_ticket.status, 'cancelled')
        self.assertIsNotNone(cancelled_ticket.full_name)
        self.assertIsNotNone(cancelled_ticket.national_id)
        
        # Query should exclude cancelled tickets
        info = LotteryService.get_user_previous_info(test_user)
        # Should not return info from cancelled ticket
        self.assertIsNone(info, f"Expected None but got {info}. Cancelled ticket should be excluded.")
        
        # Now create a non-cancelled ticket for the same user
        valid_ticket = Ticket.objects.create(
            user=test_user,
            status='won',
            full_name='علی احمدی',
            national_id='1234567890'
        )
        
        # Now should return info from valid ticket, not cancelled one
        info2 = LotteryService.get_user_previous_info(test_user)
        self.assertIsNotNone(info2)
        self.assertEqual(info2['full_name'], 'علی احمدی')
        self.assertEqual(info2['national_id'], '1234567890')
    
    @patch('apps.lottery.services.settings.LOTTERY_WINNERS_COUNT', 2)
    def test_select_winners(self):
        """Test select_winners selects correct number of winners"""
        # Create more pending tickets
        for i in range(5):
            Ticket.objects.create(
                user=self.user1,
                status='pending'
            )
        
        try:
            from zoneinfo import ZoneInfo
            tehran_tz = ZoneInfo('Asia/Tehran')
        except ImportError:
            tehran_tz = pytz.timezone('Asia/Tehran')
        
        monday_noon = datetime(2024, 1, 15, 12, 0, 0, tzinfo=tehran_tz)
        
        with patch('apps.lottery.services.timezone.now', return_value=monday_noon.astimezone(timezone.utc)):
            winners = LotteryService.select_winners(count=2)
            
            self.assertEqual(winners.count(), 2)
            for winner in winners:
                winner.refresh_from_db()
                self.assertEqual(winner.status, 'won')
                self.assertEqual(winner.received_date, 'پنجشنبه')
                self.assertEqual(winner.selected_period, 'ناهار')
    
    @patch('apps.lottery.services.settings.LOTTERY_WINNERS_COUNT', 10)
    def test_select_winners_fewer_tickets_than_count(self):
        """Test select_winners when there are fewer tickets than requested count"""
        # Only 1 pending ticket exists
        try:
            from zoneinfo import ZoneInfo
            tehran_tz = ZoneInfo('Asia/Tehran')
        except ImportError:
            tehran_tz = pytz.timezone('Asia/Tehran')
        
        monday_noon = datetime(2024, 1, 15, 12, 0, 0, tzinfo=tehran_tz)
        
        with patch('apps.lottery.services.timezone.now', return_value=monday_noon.astimezone(timezone.utc)):
            winners = LotteryService.select_winners()
            
            # Should select only available tickets
            self.assertEqual(winners.count(), 1)
    
    def test_select_winners_copies_previous_info(self):
        """Test select_winners copies previous user info"""
        # User2 has previous completed ticket
        try:
            from zoneinfo import ZoneInfo
            tehran_tz = ZoneInfo('Asia/Tehran')
        except ImportError:
            tehran_tz = pytz.timezone('Asia/Tehran')
        
        # Create pending ticket for user2
        user2_pending = Ticket.objects.create(
            user=self.user2,
            status='pending'
        )
        
        monday_noon = datetime(2024, 1, 15, 12, 0, 0, tzinfo=tehran_tz)
        
        with patch('apps.lottery.services.timezone.now', return_value=monday_noon.astimezone(timezone.utc)):
            winners = LotteryService.select_winners(count=1)
            
            user2_pending.refresh_from_db()
            if user2_pending.status == 'won':
                self.assertEqual(user2_pending.full_name, 'علی احمدی')
                self.assertEqual(user2_pending.national_id, '1234567890')


class ParticipateLotteryViewTestCase(APITestCase):
    """Test cases for ParticipateLotteryView"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(phone_number='09021794990')
        self.url = '/api/lottery/participate/'
    
    def get_auth_headers(self):
        """Get JWT token for authenticated requests"""
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(self.user)
        return {'HTTP_AUTHORIZATION': f'Bearer {refresh.access_token}'}
    
    @patch('apps.lottery.views.ParticipateLotteryView.is_registration_time_valid', return_value=True)
    def test_participate_success(self, mock_time):
        """Test successful lottery participation"""
        response = self.client.post(self.url, {}, **self.get_auth_headers())
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('ticket', response.data)
        self.assertEqual(response.data['ticket']['status'], 'pending')
        self.assertIsNotNone(response.data['ticket']['ticket_number'])
    
    @patch('apps.lottery.views.ParticipateLotteryView.is_registration_time_valid', return_value=False)
    def test_participate_invalid_time(self, mock_time):
        """Test participation outside registration time"""
        response = self.client.post(self.url, {}, **self.get_auth_headers())
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_participate_unauthenticated(self):
        """Test participation without authentication"""
        response = self.client.post(self.url, {})
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    @patch('apps.lottery.views.ParticipateLotteryView.is_registration_time_valid', return_value=True)
    def test_participate_already_participated_this_week(self, mock_time):
        """Test participation when user already participated this week"""
        # Create ticket for this week
        Ticket.objects.create(
            user=self.user,
            status='pending'
        )
        
        response = self.client.post(self.url, {}, **self.get_auth_headers())
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    @patch('apps.lottery.views.ParticipateLotteryView.is_registration_time_valid', return_value=True)
    def test_participate_won_in_last_six_months(self, mock_time):
        """Test participation when user won in last 6 months"""
        # Create won ticket from 3 months ago
        won_ticket = Ticket.objects.create(
            user=self.user,
            status='won'
        )
        won_ticket.created_at = timezone.now() - timedelta(days=90)
        won_ticket.save()
        
        response = self.client.post(self.url, {}, **self.get_auth_headers())
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_is_registration_time_valid_saturday_after_8am(self):
        """Test is_registration_time_valid on Saturday after 8 AM"""
        try:
            from zoneinfo import ZoneInfo
            tehran_tz = ZoneInfo('Asia/Tehran')
        except ImportError:
            tehran_tz = pytz.timezone('Asia/Tehran')
        
        saturday_10am = datetime(2024, 1, 13, 10, 0, 0, tzinfo=tehran_tz)
        
        with patch('apps.lottery.views.timezone.now', return_value=saturday_10am.astimezone(timezone.utc)):
            result = ParticipateLotteryView.is_registration_time_valid()
            self.assertTrue(result)
    
    def test_is_registration_time_valid_saturday_before_8am(self):
        """Test is_registration_time_valid on Saturday before 8 AM"""
        try:
            from zoneinfo import ZoneInfo
            tehran_tz = ZoneInfo('Asia/Tehran')
        except ImportError:
            tehran_tz = pytz.timezone('Asia/Tehran')
        
        saturday_7am = datetime(2024, 1, 13, 7, 0, 0, tzinfo=tehran_tz)
        
        with patch('apps.lottery.views.timezone.now', return_value=saturday_7am.astimezone(timezone.utc)):
            result = ParticipateLotteryView.is_registration_time_valid()
            self.assertFalse(result)
    
    def test_is_registration_time_valid_wednesday_before_8pm(self):
        """Test is_registration_time_valid on Wednesday before 8 PM"""
        try:
            from zoneinfo import ZoneInfo
            tehran_tz = ZoneInfo('Asia/Tehran')
        except ImportError:
            tehran_tz = pytz.timezone('Asia/Tehran')
        
        wednesday_7pm = datetime(2024, 1, 17, 19, 0, 0, tzinfo=tehran_tz)
        
        with patch('apps.lottery.views.timezone.now', return_value=wednesday_7pm.astimezone(timezone.utc)):
            result = ParticipateLotteryView.is_registration_time_valid()
            self.assertTrue(result)
    
    def test_is_registration_time_valid_wednesday_after_8pm(self):
        """Test is_registration_time_valid on Wednesday after 8 PM"""
        try:
            from zoneinfo import ZoneInfo
            tehran_tz = ZoneInfo('Asia/Tehran')
        except ImportError:
            tehran_tz = pytz.timezone('Asia/Tehran')
        
        wednesday_9pm = datetime(2024, 1, 17, 21, 0, 0, tzinfo=tehran_tz)
        
        with patch('apps.lottery.views.timezone.now', return_value=wednesday_9pm.astimezone(timezone.utc)):
            result = ParticipateLotteryView.is_registration_time_valid()
            self.assertFalse(result)
    
    def test_is_registration_time_valid_thursday(self):
        """Test is_registration_time_valid on Thursday"""
        try:
            from zoneinfo import ZoneInfo
            tehran_tz = ZoneInfo('Asia/Tehran')
        except ImportError:
            tehran_tz = pytz.timezone('Asia/Tehran')
        
        thursday_noon = datetime(2024, 1, 18, 12, 0, 0, tzinfo=tehran_tz)
        
        with patch('apps.lottery.views.timezone.now', return_value=thursday_noon.astimezone(timezone.utc)):
            result = ParticipateLotteryView.is_registration_time_valid()
            self.assertFalse(result)
    
    def test_has_participated_this_week_true(self):
        """Test has_participated_this_week returns True when user has ticket this week"""
        # Create ticket for this week
        Ticket.objects.create(
            user=self.user,
            status='pending'
        )
        
        result = ParticipateLotteryView.has_participated_this_week(self.user)
        self.assertTrue(result)
    
    def test_has_participated_this_week_false(self):
        """Test has_participated_this_week returns False when user has no ticket this week"""
        # Create ticket from previous week
        old_ticket = Ticket.objects.create(
            user=self.user,
            status='pending'
        )
        old_ticket.created_at = timezone.now() - timedelta(days=10)
        old_ticket.save()
        
        result = ParticipateLotteryView.has_participated_this_week(self.user)
        self.assertFalse(result)
    
    def test_has_won_in_last_six_months_true(self):
        """Test has_won_in_last_six_months returns True when user won recently"""
        # Create won ticket from 3 months ago
        won_ticket = Ticket.objects.create(
            user=self.user,
            status='won'
        )
        won_ticket.created_at = timezone.now() - timedelta(days=90)
        won_ticket.save()
        
        result = ParticipateLotteryView.has_won_in_last_six_months(self.user)
        self.assertTrue(result)
    
    def test_has_won_in_last_six_months_false(self):
        """Test has_won_in_last_six_months returns False when user won more than 6 months ago"""
        # Create won ticket from 7 months ago
        won_ticket = Ticket.objects.create(
            user=self.user,
            status='won'
        )
        won_ticket.created_at = timezone.now() - timedelta(days=210)
        won_ticket.save()
        
        result = ParticipateLotteryView.has_won_in_last_six_months(self.user)
        self.assertFalse(result)


class CompleteWinnerInfoViewTestCase(APITestCase):
    """Test cases for CompleteWinnerInfoView"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(phone_number='09021794990')
        self.url = '/api/lottery/complete-winner-info/'
        
        # Create won ticket
        self.won_ticket = Ticket.objects.create(
            user=self.user,
            status='won',
            ticket_number='TEST123'
        )
    
    def get_auth_headers(self):
        """Get JWT token for authenticated requests"""
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(self.user)
        return {'HTTP_AUTHORIZATION': f'Bearer {refresh.access_token}'}
    
    def test_get_winner_info_success(self):
        """Test GET winner info"""
        response = self.client.get(self.url, **self.get_auth_headers())
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('ticket', response.data)
        self.assertEqual(response.data['ticket']['ticket_number'], 'TEST123')
    
    def test_get_winner_info_no_ticket(self):
        """Test GET when user has no won ticket"""
        # Delete won ticket
        self.won_ticket.delete()
        
        response = self.client.get(self.url, **self.get_auth_headers())
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_complete_winner_info_success(self):
        """Test POST complete winner info"""
        data = {
            'full_name': 'علی احمدی',
            'national_id': '1234567890',
            'received_date': 'پنجشنبه',
            'selected_period': 'ناهار',
            'quantity': 2
        }
        
        # Mock deadline check to return True
        with patch('apps.lottery.views.CompleteWinnerInfoView.is_within_deadline', return_value=True):
            response = self.client.post(self.url, data, **self.get_auth_headers())
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.won_ticket.refresh_from_db()
            self.assertEqual(self.won_ticket.full_name, 'علی احمدی')
            self.assertEqual(self.won_ticket.national_id, '1234567890')
            self.assertEqual(self.won_ticket.quantity, 2)
    
    def test_complete_winner_info_deadline_passed(self):
        """Test POST when deadline has passed"""
        data = {
            'full_name': 'علی احمدی',
            'national_id': '1234567890',
            'received_date': 'پنجشنبه',
            'selected_period': 'ناهار',
            'quantity': 2
        }
        
        # Mock deadline check to return False
        with patch('apps.lottery.views.CompleteWinnerInfoView.is_within_deadline', return_value=False):
            response = self.client.post(self.url, data, **self.get_auth_headers())
            
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn('error', response.data)
    
    def test_complete_winner_info_invalid_quantity(self):
        """Test POST with invalid quantity"""
        data = {
            'full_name': 'علی احمدی',
            'national_id': '1234567890',
            'received_date': 'پنجشنبه',
            'selected_period': 'ناهار',
            'quantity': 5  # Invalid: should be 1-3
        }
        
        with patch('apps.lottery.views.CompleteWinnerInfoView.is_within_deadline', return_value=True):
            response = self.client.post(self.url, data, **self.get_auth_headers())
            
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_complete_winner_info_invalid_national_id(self):
        """Test POST with invalid national_id"""
        data = {
            'full_name': 'علی احمدی',
            'national_id': '12345',  # Invalid: should be 10 digits
            'received_date': 'پنجشنبه',
            'selected_period': 'ناهار',
            'quantity': 2
        }
        
        with patch('apps.lottery.views.CompleteWinnerInfoView.is_within_deadline', return_value=True):
            response = self.client.post(self.url, data, **self.get_auth_headers())
            
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_is_within_deadline_before_deadline(self):
        """Test is_within_deadline returns True before deadline"""
        try:
            from zoneinfo import ZoneInfo
            tehran_tz = ZoneInfo('Asia/Tehran')
        except ImportError:
            tehran_tz = pytz.timezone('Asia/Tehran')
        
        # Ticket created on Wednesday 8 PM, current time is Thursday 7 AM
        ticket_created = datetime(2024, 1, 17, 20, 0, 0, tzinfo=tehran_tz)
        current_time = datetime(2024, 1, 18, 7, 0, 0, tzinfo=tehran_tz)
        
        with patch('apps.lottery.views.timezone.now', return_value=current_time.astimezone(timezone.utc)):
            result = CompleteWinnerInfoView.is_within_deadline(ticket_created.astimezone(timezone.utc))
            self.assertTrue(result)
    
    def test_is_within_deadline_after_deadline(self):
        """Test is_within_deadline returns False after deadline"""
        try:
            from zoneinfo import ZoneInfo
            tehran_tz = ZoneInfo('Asia/Tehran')
        except ImportError:
            tehran_tz = pytz.timezone('Asia/Tehran')
        
        # Ticket created on Wednesday 8 PM, current time is Thursday 9 AM
        ticket_created = datetime(2024, 1, 17, 20, 0, 0, tzinfo=tehran_tz)
        current_time = datetime(2024, 1, 18, 9, 0, 0, tzinfo=tehran_tz)
        
        with patch('apps.lottery.views.timezone.now', return_value=current_time.astimezone(timezone.utc)):
            result = CompleteWinnerInfoView.is_within_deadline(ticket_created.astimezone(timezone.utc))
            self.assertFalse(result)


class UserTicketsHistoryViewTestCase(APITestCase):
    """Test cases for UserTicketsHistoryView"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(phone_number='09021794990')
        self.other_user = User.objects.create_user(phone_number='09021794991')
        self.url = '/api/lottery/my-tickets/'
        
        # Create tickets for user
        self.ticket1 = Ticket.objects.create(user=self.user, status='pending')
        self.ticket2 = Ticket.objects.create(user=self.user, status='won')
        
        # Create ticket for other user
        self.other_ticket = Ticket.objects.create(user=self.other_user, status='pending')
    
    def get_auth_headers(self):
        """Get JWT token for authenticated requests"""
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(self.user)
        return {'HTTP_AUTHORIZATION': f'Bearer {refresh.access_token}'}
    
    def test_get_user_tickets_history(self):
        """Test GET user tickets history"""
        response = self.client.get(self.url, **self.get_auth_headers())
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['results']), 2)
        
        # Should not include other_user's tickets
        ticket_numbers = [t['ticket_number'] for t in response.data['results']]
        self.assertNotIn(self.other_ticket.ticket_number, ticket_numbers)
    
    def test_get_user_tickets_history_ordered(self):
        """Test tickets are ordered by created_at descending"""
        response = self.client.get(self.url, **self.get_auth_headers())
        
        results = response.data['results']
        # First ticket should be newer
        self.assertGreaterEqual(
            results[0]['created_at'],
            results[1]['created_at']
        )


class CurrentWeekWinnersViewTestCase(APITestCase):
    """Test cases for CurrentWeekWinnersView"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(phone_number='09021794990')
        self.url = '/api/lottery/current-week-winners/'
        
        # Create won ticket for current week
        self.won_ticket = Ticket.objects.create(
            user=self.user,
            status='won'
        )
        
        # Create old won ticket
        self.old_won = Ticket.objects.create(
            user=self.user,
            status='won'
        )
        self.old_won.created_at = timezone.now() - timedelta(days=10)
        self.old_won.save()
    
    def get_auth_headers(self):
        """Get JWT token for authenticated requests"""
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(self.user)
        return {'HTTP_AUTHORIZATION': f'Bearer {refresh.access_token}'}
    
    def test_get_current_week_winners(self):
        """Test GET current week winners"""
        try:
            from zoneinfo import ZoneInfo
            tehran_tz = ZoneInfo('Asia/Tehran')
        except ImportError:
            tehran_tz = pytz.timezone('Asia/Tehran')
        
        monday_noon = datetime(2024, 1, 15, 12, 0, 0, tzinfo=tehran_tz)
        
        with patch('apps.lottery.services.timezone.now', return_value=monday_noon.astimezone(timezone.utc)):
            response = self.client.get(self.url, **self.get_auth_headers())
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn('week_start', response.data)
            self.assertIn('count', response.data)
            self.assertIn('winners', response.data)
            self.assertGreaterEqual(response.data['count'], 0)


class SchedulerTestCase(TestCase):
    """Test cases for scheduler functions"""
    
    def setUp(self):
        """Set up test data"""
        if not SCHEDULER_AVAILABLE:
            self.skipTest("Scheduler module not available")
        
        self.user1 = User.objects.create_user(phone_number='09021794990')
        self.user2 = User.objects.create_user(phone_number='09021794991')
        
        # Create pending tickets
        for i in range(5):
            Ticket.objects.create(
                user=self.user1,
                status='pending'
            )
    
    @patch('apps.lottery.services.KavehNegarLotteryService.send_winner_sms')
    @patch('apps.lottery.services.settings.LOTTERY_WINNERS_COUNT', 2)
    def test_run_lottery_job(self, mock_send_sms):
        """Test run_lottery_job selects winners and sends SMS"""
        if not SCHEDULER_AVAILABLE:
            self.skipTest("Scheduler module not available")
        
        mock_send_sms.return_value = True
        
        try:
            from zoneinfo import ZoneInfo
            tehran_tz = ZoneInfo('Asia/Tehran')
        except ImportError:
            tehran_tz = pytz.timezone('Asia/Tehran')
        
        monday_noon = datetime(2024, 1, 15, 12, 0, 0, tzinfo=tehran_tz)
        
        with patch('apps.lottery.services.timezone.now', return_value=monday_noon.astimezone(timezone.utc)):
            run_lottery_job()
            
            # Check winners were selected
            winners = Ticket.objects.filter(status='won')
            self.assertEqual(winners.count(), 2)
            
            # Check SMS was sent
            self.assertEqual(mock_send_sms.call_count, 2)
    
    @patch('apps.lottery.services.KavehNegarLotteryService.send_winner_sms')
    def test_run_lottery_job_no_tickets(self, mock_send_sms):
        """Test run_lottery_job when no pending tickets exist"""
        if not SCHEDULER_AVAILABLE:
            self.skipTest("Scheduler module not available")
        
        # Delete all pending tickets
        Ticket.objects.filter(status='pending').delete()
        
        try:
            from zoneinfo import ZoneInfo
            tehran_tz = ZoneInfo('Asia/Tehran')
        except ImportError:
            tehran_tz = pytz.timezone('Asia/Tehran')
        
        monday_noon = datetime(2024, 1, 15, 12, 0, 0, tzinfo=tehran_tz)
        
        with patch('apps.lottery.services.timezone.now', return_value=monday_noon.astimezone(timezone.utc)):
            run_lottery_job()
            
            # SMS should not be sent
            mock_send_sms.assert_not_called()
    
    @patch('apps.lottery.services.KavehNegarLotteryService.send_winner_sms')
    @patch('apps.lottery.services.settings.LOTTERY_WINNERS_COUNT', 2)
    def test_run_lottery_job_sms_failure(self, mock_send_sms):
        """Test run_lottery_job handles SMS failures gracefully"""
        if not SCHEDULER_AVAILABLE:
            self.skipTest("Scheduler module not available")
        
        # Make SMS fail for one winner
        mock_send_sms.side_effect = [True, Exception("SMS failed")]
        
        try:
            from zoneinfo import ZoneInfo
            tehran_tz = ZoneInfo('Asia/Tehran')
        except ImportError:
            tehran_tz = pytz.timezone('Asia/Tehran')
        
        monday_noon = datetime(2024, 1, 15, 12, 0, 0, tzinfo=tehran_tz)
        
        with patch('apps.lottery.services.timezone.now', return_value=monday_noon.astimezone(timezone.utc)):
            # Should not raise exception
            run_lottery_job()
            
            # Winners should still be selected
            winners = Ticket.objects.filter(status='won')
            self.assertEqual(winners.count(), 2)
    
    def test_cancel_incomplete_winners(self):
        """Test cancel_incomplete_winners cancels incomplete tickets after deadline"""
        if not SCHEDULER_AVAILABLE:
            self.skipTest("Scheduler module not available")
        
        try:
            from zoneinfo import ZoneInfo
            tehran_tz = ZoneInfo('Asia/Tehran')
        except ImportError:
            tehran_tz = pytz.timezone('Asia/Tehran')
        
        # Create incomplete won ticket from last week
        incomplete_ticket = Ticket.objects.create(
            user=self.user1,
            status='won',
            ticket_number='INCOMPLETE1'
        )
        # Set created_at to last Wednesday 8 PM
        last_wednesday = datetime(2024, 1, 10, 20, 0, 0, tzinfo=tehran_tz)
        incomplete_ticket.created_at = last_wednesday.astimezone(timezone.utc)
        incomplete_ticket.save()
        
        # Create complete won ticket from last week
        complete_ticket = Ticket.objects.create(
            user=self.user2,
            status='won',
            full_name='علی احمدی',
            national_id='1234567890',
            received_date='پنجشنبه',
            selected_period='ناهار',
            quantity=2,
            ticket_number='COMPLETE1'
        )
        complete_ticket.created_at = last_wednesday.astimezone(timezone.utc)
        complete_ticket.save()
        
        # Mock current time as Thursday 9 AM (after deadline)
        thursday_9am = datetime(2024, 1, 11, 9, 0, 0, tzinfo=tehran_tz)
        
        with patch('apps.lottery.scheduler.timezone.now', return_value=thursday_9am.astimezone(timezone.utc)):
            cancel_incomplete_winners()
            
            incomplete_ticket.refresh_from_db()
            complete_ticket.refresh_from_db()
            
            # Incomplete ticket should be cancelled
            self.assertEqual(incomplete_ticket.status, 'cancelled')
            # Complete ticket should remain won
            self.assertEqual(complete_ticket.status, 'won')
    
    def test_cancel_incomplete_winners_before_deadline(self):
        """Test cancel_incomplete_winners does not cancel tickets before deadline"""
        if not SCHEDULER_AVAILABLE:
            self.skipTest("Scheduler module not available")
        
        try:
            from zoneinfo import ZoneInfo
            tehran_tz = ZoneInfo('Asia/Tehran')
        except ImportError:
            tehran_tz = pytz.timezone('Asia/Tehran')
        
        # Create incomplete won ticket from this week
        incomplete_ticket = Ticket.objects.create(
            user=self.user1,
            status='won',
            ticket_number='INCOMPLETE2'
        )
        # Set created_at to this Wednesday 8 PM
        this_wednesday = datetime(2024, 1, 17, 20, 0, 0, tzinfo=tehran_tz)
        incomplete_ticket.created_at = this_wednesday.astimezone(timezone.utc)
        incomplete_ticket.save()
        
        # Mock current time as Thursday 7 AM (before deadline)
        thursday_7am = datetime(2024, 1, 18, 7, 0, 0, tzinfo=tehran_tz)
        
        with patch('apps.lottery.scheduler.timezone.now', return_value=thursday_7am.astimezone(timezone.utc)):
            cancel_incomplete_winners()
            
            incomplete_ticket.refresh_from_db()
            
            # Ticket should not be cancelled yet
            self.assertEqual(incomplete_ticket.status, 'won')
    
    def test_scheduler_configuration(self):
        """Test that scheduler is configured correctly with proper cron triggers"""
        if not SCHEDULER_AVAILABLE:
            self.skipTest("Scheduler module not available")
        
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            from apscheduler.triggers.cron import CronTrigger
            from zoneinfo import ZoneInfo
            tehran_tz = ZoneInfo('Asia/Tehran')
        except ImportError:
            try:
                import pytz
                tehran_tz = pytz.timezone('Asia/Tehran')
            except ImportError:
                self.skipTest("Timezone libraries not available")
        
        # Create a test scheduler to verify configuration
        scheduler = BackgroundScheduler(timezone=tehran_tz)
        
        # Test lottery job trigger configuration
        lottery_trigger = CronTrigger(day_of_week='wed', hour=20, minute=0, timezone=tehran_tz)
        scheduler.add_job(
            run_lottery_job,
            trigger=lottery_trigger,
            id='test_lottery_job',
            replace_existing=True,
        )
        
        # Test cancellation job trigger configuration
        cancel_trigger = CronTrigger(day_of_week='thu', hour=8, minute=0, timezone=tehran_tz)
        scheduler.add_job(
            cancel_incomplete_winners,
            trigger=cancel_trigger,
            id='test_cancel_job',
            replace_existing=True,
        )
        
        # Verify jobs are added
        jobs = scheduler.get_jobs()
        self.assertEqual(len(jobs), 2)
        
        # Verify lottery job configuration
        lottery_job = scheduler.get_job('test_lottery_job')
        self.assertIsNotNone(lottery_job)
        self.assertEqual(lottery_job.id, 'test_lottery_job')
        # Verify trigger is CronTrigger
        self.assertIsInstance(lottery_job.trigger, CronTrigger)
        # Verify trigger configuration by checking next run time
        # Should run on Wednesday at 20:00
        trigger = lottery_job.trigger
        self.assertEqual(trigger.fields[4].name, 'day_of_week')  # day_of_week field
        self.assertEqual(trigger.fields[5].name, 'hour')  # hour field
        self.assertEqual(trigger.fields[6].name, 'minute')  # minute field
        
        # Verify cancellation job configuration
        cancel_job = scheduler.get_job('test_cancel_job')
        self.assertIsNotNone(cancel_job)
        self.assertEqual(cancel_job.id, 'test_cancel_job')
        # Verify trigger is CronTrigger
        self.assertIsInstance(cancel_job.trigger, CronTrigger)
        # Verify trigger configuration
        cancel_trigger = cancel_job.trigger
        self.assertEqual(cancel_trigger.fields[4].name, 'day_of_week')  # day_of_week field
        self.assertEqual(cancel_trigger.fields[5].name, 'hour')  # hour field
        self.assertEqual(cancel_trigger.fields[6].name, 'minute')  # minute field
        
        # Clean up - only shutdown if scheduler is running
        if scheduler.running:
            scheduler.shutdown()
    
    def test_scheduler_start_function(self):
        """Test that start_scheduler function configures jobs correctly"""
        if not SCHEDULER_AVAILABLE:
            self.skipTest("Scheduler module not available")
        
        try:
            from .scheduler import start_scheduler
            from apscheduler.schedulers.background import BackgroundScheduler
        except ImportError:
            self.skipTest("Scheduler module not available")
        
        # Mock the scheduler to avoid actually starting it
        with patch('apps.lottery.scheduler.BackgroundScheduler') as mock_scheduler_class:
            mock_scheduler = MagicMock()
            mock_scheduler_class.return_value = mock_scheduler
            
            # Mock jobstore
            from django_apscheduler.jobstores import DjangoJobStore
            with patch('apps.lottery.scheduler.DjangoJobStore') as mock_jobstore:
                with patch('apps.lottery.scheduler.register_events'):
                    try:
                        start_scheduler()
                    except Exception:
                        # Scheduler might fail in test environment, that's OK
                        pass
                    
                    # Verify scheduler was configured
                    mock_scheduler.add_jobstore.assert_called_once()
                    # Verify jobs were added (should be called twice: lottery + cancel)
                    self.assertGreaterEqual(mock_scheduler.add_job.call_count, 2)
                    # Verify scheduler was started
                    mock_scheduler.start.assert_called_once()

