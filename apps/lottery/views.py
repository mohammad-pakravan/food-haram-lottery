from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings

from .models import Ticket
from .serializers import TicketSerializer, TicketCreateSerializer, WinnerInfoSerializer
from .services import LotteryService


class ParticipateLotteryView(APIView):
    """
    API endpoint for users to participate in lottery
    
    کاربران می‌توانند با ارسال یک درخواست احراز هویت شده در قرعه کشی شرکت کنند.
    یک Ticket جدید با status 'pending' ایجاد می‌شود.
    
    شرایط:
    - زمان ثبت نام: از ساعت 8 صبح روز شنبه تا ساعت 8 عصر چهارشنبه (به وقت تهران)
    - کاربر در 6 ماه گذشته نباید برنده شده باشد
    """
    permission_classes = [IsAuthenticated]
    
    @staticmethod
    def is_registration_time_valid():
        """
        Check if current time is within registration period
        Registration: Saturday 8 AM to Wednesday 8 PM (Tehran time)
        """
        try:
            from zoneinfo import ZoneInfo
            tehran_tz = ZoneInfo('Asia/Tehran')
        except ImportError:
            # Fallback for older Python versions
            import pytz
            tehran_tz = pytz.timezone('Asia/Tehran')
        
        now_tehran = timezone.now().astimezone(tehran_tz)
        current_weekday = now_tehran.weekday()  # 0=Monday, 6=Sunday
        current_hour = now_tehran.hour
        
        # Saturday = 5, Sunday = 6
        # Monday = 0, Tuesday = 1, Wednesday = 2
        
        # Check if it's Saturday (5) and after 8 AM
        if current_weekday == 5:  # Saturday
            return current_hour >= 8
        
        # Check if it's Sunday (6) - all day
        if current_weekday == 6:  # Sunday
            return True
        
        # Check if it's Monday (0) or Tuesday (1) - all day
        if current_weekday in [0, 1]:  # Monday, Tuesday
            return True
        
        # Check if it's Wednesday (2) and before 8 PM (20:00)
        if current_weekday == 2:  # Wednesday
            return current_hour < 20
        
        # Thursday (3), Friday (4) - not allowed
        return False
    
    @staticmethod
    def get_current_week_start():
        """
        Get the start of current registration week (Saturday 8 AM Tehran time)
        Returns datetime in UTC (timezone-aware)
        """
        try:
            from zoneinfo import ZoneInfo
            tehran_tz = ZoneInfo('Asia/Tehran')
        except ImportError:
            import pytz
            tehran_tz = pytz.timezone('Asia/Tehran')
        
        now_tehran = timezone.now().astimezone(tehran_tz)
        current_weekday = now_tehran.weekday()  # 0=Monday, 6=Sunday
        
        # Calculate days to subtract to get to Saturday
        # Saturday = 5
        if current_weekday == 5:  # Saturday
            if now_tehran.hour < 8:
                # Before 8 AM, go to previous Saturday
                days_to_saturday = 7
            else:
                # After 8 AM, this is the current Saturday
                days_to_saturday = 0
        else:
            # Calculate days to last Saturday
            days_to_saturday = (current_weekday - 5) % 7
            if days_to_saturday == 0:
                days_to_saturday = 7
        
        # Get Saturday 8 AM of current week
        saturday_8am = now_tehran.replace(hour=8, minute=0, second=0, microsecond=0)
        saturday_8am = saturday_8am - timedelta(days=days_to_saturday)
        
        # Convert back to UTC and return timezone-aware
        return saturday_8am.astimezone(timezone.utc)
    
    @staticmethod
    def has_participated_this_week(user):
        """
        Check if user has already participated in current week
        Current week: Saturday 8 AM to Wednesday 8 PM
        """
        week_start = ParticipateLotteryView.get_current_week_start()
        
        has_ticket = Ticket.objects.filter(
            user=user,
            created_at__gte=week_start
        ).exists()
        
        return has_ticket
    
    @staticmethod
    def has_won_in_last_six_months(user):
        """
        Check if user has won in the last 6 months
        """
        six_months_ago = timezone.now() - timedelta(days=180)
        
        won_tickets = Ticket.objects.filter(
            user=user,
            status='won',
            created_at__gte=six_months_ago
        ).exists()
        
        return won_tickets
    
    @swagger_auto_schema(
        operation_description="شرکت در قرعه کشی. با ارسال این درخواست، یک بلیط جدید با شماره ژتون رندوم برای کاربر ایجاد می‌شود. زمان ثبت نام: شنبه 8 صبح تا چهارشنبه 8 عصر (به وقت تهران).",
        request_body=TicketCreateSerializer,
        responses={
            201: openapi.Response(
                description="بلیط با موفقیت ایجاد شد",
                schema=TicketSerializer
            ),
            400: openapi.Response(description="زمان ثبت نام به پایان رسیده یا کاربر در 6 ماه گذشته برنده شده است"),
            401: openapi.Response(description="نیاز به احراز هویت"),
        },
        security=[{'Bearer': []}],
        tags=['Lottery']
    )
    def post(self, request):
        """
        Create a new lottery ticket for authenticated user
        """
        # Check registration time
        if not self.is_registration_time_valid():
            return Response(
                {
                    'error': 'زمان ثبت نام به پایان رسیده است. زمان ثبت نام: شنبه ساعت 8 صبح تا چهارشنبه ساعت 8 عصر (به وقت تهران)'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if user has already participated this week
        if self.has_participated_this_week(request.user):
            return Response(
                {
                    'error': 'شما در این هفته قبلاً در قرعه کشی شرکت کرده‌اید. هر کاربر فقط یک بار در هفته می‌تواند شرکت کند.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if user has won in last 6 months
        if self.has_won_in_last_six_months(request.user):
            return Response(
                {
                    'error': 'شما در 6 ماه گذشته برنده قرعه کشی شده‌اید و نمی‌توانید دوباره شرکت کنید'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create ticket for authenticated user
        ticket = Ticket.objects.create(
            user=request.user,
            status='pending'
            # ticket_number will be auto-generated in save() method
            # Other fields remain null/blank
        )
        
        serializer = TicketSerializer(ticket)
        
        return Response(
            {
                'message': 'شما با موفقیت در قرعه کشی شرکت کردید',
                'ticket': serializer.data
            },
            status=status.HTTP_201_CREATED
        )


class CompleteWinnerInfoView(APIView):
    """
    API endpoint for winners to complete their information
    
    برندگان می‌توانند اطلاعات خود را تکمیل کنند.
    مهلت: تا پنجشنبه ساعت 8 صبح
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="دریافت اطلاعات تیکت برنده. اگر کاربر قبلاً اطلاعات را پر کرده باشد، به‌صورت خودکار نمایش داده می‌شود.",
        responses={
            200: openapi.Response(
                description="اطلاعات تیکت برنده",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'ticket': openapi.Schema(type=openapi.TYPE_OBJECT),
                        'has_previous_info': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='آیا اطلاعات قبلی وجود دارد')
                    }
                )
            ),
            404: openapi.Response(description="تیکت برنده یافت نشد"),
            401: openapi.Response(description="نیاز به احراز هویت"),
        },
        security=[{'Bearer': []}],
        tags=['Lottery']
    )
    def get(self, request):
        """
        Get current winner ticket with pre-filled information if available
        """
        # Check if user has a won ticket
        try:
            ticket = Ticket.objects.get(
                user=request.user,
                status='won'
            )
        except Ticket.DoesNotExist:
            return Response(
                {'error': 'شما برنده قرعه کشی نشده‌اید'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if ticket already has information (auto-filled from previous win)
        ticket_serializer = TicketSerializer(ticket)
        
        response_data = {
            'ticket': ticket_serializer.data,
            'has_previous_info': bool(ticket.full_name and ticket.national_id)
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        operation_description="تکمیل اطلاعات برنده. برندگان باید تا پنجشنبه ساعت 8 صبح اطلاعات خود را تکمیل کنند.",
        request_body=WinnerInfoSerializer,
        responses={
            200: openapi.Response(
                description="اطلاعات با موفقیت ثبت شد",
                schema=TicketSerializer
            ),
            400: openapi.Response(description="خطا در داده‌های ارسالی یا مهلت به پایان رسیده"),
            404: openapi.Response(description="تیکت برنده یافت نشد"),
            401: openapi.Response(description="نیاز به احراز هویت"),
        },
        security=[{'Bearer': []}],
        tags=['Lottery']
    )
    def post(self, request):
        """
        Complete winner information
        """
        serializer = WinnerInfoSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if user has a won ticket
        try:
            ticket = Ticket.objects.get(
                user=request.user,
                status='won'
            )
        except Ticket.DoesNotExist:
            return Response(
                {'error': 'شما برنده قرعه کشی نشده‌اید'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check deadline (Thursday 8 AM Tehran time)
        if not self.is_within_deadline(ticket.created_at):
            return Response(
                {
                    'error': 'مهلت تکمیل اطلاعات به پایان رسیده است. مهلت: تا پنجشنبه ساعت 8 صبح'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update ticket information
        ticket.full_name = serializer.validated_data['full_name']
        ticket.national_id = serializer.validated_data['national_id']
        ticket.received_date = serializer.validated_data['received_date']
        ticket.selected_period = serializer.validated_data['selected_period']
        ticket.quantity = serializer.validated_data['quantity']
        ticket.save()
        
        ticket_serializer = TicketSerializer(ticket)
        
        return Response(
            {
                'message': 'اطلاعات شما با موفقیت ثبت شد',
                'ticket': ticket_serializer.data
            },
            status=status.HTTP_200_OK
        )
    
    @staticmethod
    def is_within_deadline(ticket_created_at):
        """
        Check if current time is within deadline (Thursday 8 AM Tehran time)
        Deadline: Until Thursday 8 AM after winning (Wednesday 8 PM)
        """
        try:
            from zoneinfo import ZoneInfo
            tehran_tz = ZoneInfo('Asia/Tehran')
        except ImportError:
            import pytz
            tehran_tz = pytz.timezone('Asia/Tehran')
        
        now_tehran = timezone.now().astimezone(tehran_tz)
        ticket_created_tehran = ticket_created_at.astimezone(tehran_tz)
        
        # Calculate the Thursday 8 AM after the ticket was created (Wednesday 8 PM)
        # If ticket was created on Wednesday 8 PM, deadline is Thursday 8 AM (next day)
        ticket_weekday = ticket_created_tehran.weekday()
        ticket_hour = ticket_created_tehran.hour
        
        # Find the next Thursday 8 AM after ticket creation
        if ticket_weekday == 2:  # Wednesday
            if ticket_hour >= 20:  # After 8 PM
                # Deadline is next day (Thursday) 8 AM
                days_to_thursday = 1
            else:
                # Before 8 PM, shouldn't happen for won tickets, but handle it
                days_to_thursday = 1
        else:
            # Calculate days to next Thursday
            days_to_thursday = (3 - ticket_weekday) % 7
            if days_to_thursday == 0:
                days_to_thursday = 7
        
        deadline = ticket_created_tehran.replace(hour=8, minute=0, second=0, microsecond=0)
        deadline = deadline + timedelta(days=days_to_thursday)
        
        # Check if current time is before deadline
        return now_tehran < deadline


class UserTicketsHistoryView(APIView):
    """
    API endpoint for users to view their lottery participation history
    
    نمایش سوابق ثبت نام کاربر در قرعه کشی
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="دریافت سوابق ثبت نام کاربر در قرعه کشی. تمام تیکت‌های کاربر به ترتیب تاریخ (جدیدترین اول) نمایش داده می‌شود.",
        responses={
            200: openapi.Response(
                description="لیست تیکت‌های کاربر",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'count': openapi.Schema(type=openapi.TYPE_INTEGER, description='تعداد کل تیکت‌ها'),
                        'results': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(type=openapi.TYPE_OBJECT)
                        )
                    }
                )
            ),
            401: openapi.Response(description="نیاز به احراز هویت"),
        },
        security=[{'Bearer': []}],
        tags=['Lottery']
    )
    def get(self, request):
        """
        Get user's lottery participation history
        """
        # Get all tickets for the authenticated user
        tickets = Ticket.objects.filter(
            user=request.user
        ).order_by('-created_at')
        
        # Serialize tickets
        serializer = TicketSerializer(tickets, many=True)
        
        return Response(
            {
                'count': tickets.count(),
                'results': serializer.data
            },
            status=status.HTTP_200_OK
        )


class CurrentWeekWinnersView(APIView):
    """
    API endpoint to view current week's winners
    
    نمایش برندگان هفته جاری
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="دریافت لیست برندگان هفته جاری. هفته جاری از شنبه ساعت 8 صبح تا چهارشنبه ساعت 8 عصر (به وقت تهران) محاسبه می‌شود.",
        responses={
            200: openapi.Response(
                description="لیست برندگان هفته جاری",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'week_start': openapi.Schema(type=openapi.TYPE_STRING, description='شروع هفته (شنبه 8 صبح)'),
                        'count': openapi.Schema(type=openapi.TYPE_INTEGER, description='تعداد برندگان'),
                        'winners': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(type=openapi.TYPE_OBJECT)
                        )
                    }
                )
            ),
            401: openapi.Response(description="نیاز به احراز هویت"),
        },
        security=[{'Bearer': []}],
        tags=['Lottery']
    )
    def get(self, request):
        """
        Get current week's winners
        """
        # Get current week winners
        winners = LotteryService.get_current_week_winners()
        
        # Serialize winners
        serializer = TicketSerializer(winners, many=True)
        
        # Get week start for display
        week_start = LotteryService.get_current_week_start()
        try:
            from zoneinfo import ZoneInfo
            tehran_tz = ZoneInfo('Asia/Tehran')
        except ImportError:
            import pytz
            tehran_tz = pytz.timezone('Asia/Tehran')
        
        week_start_tehran = week_start.astimezone(tehran_tz)
        
        return Response(
            {
                'week_start': week_start_tehran.strftime('%Y-%m-%d %H:%M:%S %Z'),
                'count': winners.count(),
                'winners': serializer.data
            },
            status=status.HTTP_200_OK
        )

