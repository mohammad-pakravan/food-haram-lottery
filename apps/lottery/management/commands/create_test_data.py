"""
Management command to create test data for lottery system
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import connection
from datetime import timedelta
from apps.lottery.models import Ticket
import random

User = get_user_model()


class Command(BaseCommand):
    help = 'Create test data for lottery system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--users',
            type=int,
            default=10,
            help='Number of users to create (default: 10)'
        )
        parser.add_argument(
            '--phone-prefix',
            type=str,
            default='0902179499',
            help='Phone number prefix (default: 0902179499)'
        )

    def handle(self, *args, **options):
        num_users = options['users']
        phone_prefix = options['phone_prefix']
        
        self.stdout.write(self.style.SUCCESS(f'Creating {num_users} test users...'))
        
        # Create users
        users = []
        for i in range(num_users):
            phone_number = f"{phone_prefix}{i}"
            user, created = User.objects.get_or_create(
                phone_number=phone_number,
                defaults={'is_phone_verified': True}
            )
            if created:
                users.append(user)
                self.stdout.write(self.style.SUCCESS(f'  Created user: {phone_number}'))
            else:
                users.append(user)
                self.stdout.write(self.style.WARNING(f'  User already exists: {phone_number}'))
        
        # Create tickets with different statuses
        self.stdout.write(self.style.SUCCESS('\nCreating test tickets...'))
        
        now = timezone.now()
        week_start = self.get_current_week_start(now)
        
        # Create pending tickets for current week
        pending_count = 0
        for i, user in enumerate(users[:5]):
            ticket = Ticket.objects.create(
                user=user,
                status='pending'
            )
            # Set created_at to current week using direct SQL update
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE lottery_tickets SET created_at = %s WHERE id = %s",
                    [week_start + timedelta(days=i % 3), ticket.id]
                )
            pending_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'  Created {pending_count} pending tickets'))
        
        # Create won tickets (some from current week, some from previous weeks)
        won_count = 0
        for i, user in enumerate(users[5:8]):
            # Create ticket first without received_date to avoid DateField issue
            ticket = Ticket.objects.create(
                user=user,
                status='won',
                full_name=f'کاربر تست {i+1}',
                national_id=f'123456789{i}',
                selected_period='ناهار',
                quantity=random.randint(1, 3)
            )
            # Update received_date and created_at using direct SQL
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE lottery_tickets SET received_date = %s, created_at = %s WHERE id = %s",
                    ['پنجشنبه', week_start + timedelta(days=i % 3), ticket.id]
                )
            won_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'  Created {won_count} won tickets (current week)'))
        
        # Create old won tickets (more than 6 months ago)
        old_won_count = 0
        for i, user in enumerate(users[8:10]):
            # Create ticket first without received_date to avoid DateField issue
            ticket = Ticket.objects.create(
                user=user,
                status='won',
                full_name=f'کاربر قدیمی {i+1}',
                national_id=f'987654321{i}',
                selected_period='ناهار',
                quantity=2
            )
            # Update received_date and created_at using direct SQL
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE lottery_tickets SET received_date = %s, created_at = %s WHERE id = %s",
                    ['پنجشنبه', now - timedelta(days=210), ticket.id]
                )
            old_won_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'  Created {old_won_count} old won tickets (7 months ago)'))
        
        # Create cancelled tickets
        cancelled_count = 0
        for i, user in enumerate(users[:2]):
            # Create ticket first without received_date to avoid DateField issue
            ticket = Ticket.objects.create(
                user=user,
                status='cancelled',
                full_name=f'کاربر لغو شده {i+1}',
                national_id=f'111111111{i}',
                selected_period='ناهار',
                quantity=1
            )
            # Update received_date and created_at using direct SQL
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE lottery_tickets SET received_date = %s, created_at = %s WHERE id = %s",
                    ['پنجشنبه', week_start + timedelta(days=i), ticket.id]
                )
            cancelled_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'  Created {cancelled_count} cancelled tickets'))
        
        self.stdout.write(self.style.SUCCESS(f'\n✅ Test data created successfully!'))
        self.stdout.write(self.style.SUCCESS(f'   - Users: {len(users)}'))
        self.stdout.write(self.style.SUCCESS(f'   - Pending tickets: {pending_count}'))
        self.stdout.write(self.style.SUCCESS(f'   - Won tickets (current week): {won_count}'))
        self.stdout.write(self.style.SUCCESS(f'   - Old won tickets: {old_won_count}'))
        self.stdout.write(self.style.SUCCESS(f'   - Cancelled tickets: {cancelled_count}'))
    
    def get_current_week_start(self, now):
        """
        Get the start of current lottery week (Saturday 8 AM Tehran time)
        """
        try:
            from zoneinfo import ZoneInfo
            tehran_tz = ZoneInfo('Asia/Tehran')
        except ImportError:
            import pytz
            tehran_tz = pytz.timezone('Asia/Tehran')
        
        # Convert to Tehran timezone
        now_tehran = now.astimezone(tehran_tz)
        
        # Find the most recent Saturday 8 AM
        days_since_saturday = (now_tehran.weekday() - 5) % 7
        
        if days_since_saturday == 0:
            # Today is Saturday
            if now_tehran.hour < 8:
                # Before 8 AM, go to previous Saturday
                days_since_saturday = 7
        
        # Calculate Saturday 8 AM
        saturday_8am = now_tehran.replace(hour=8, minute=0, second=0, microsecond=0)
        saturday_8am = saturday_8am - timedelta(days=days_since_saturday)
        
        # Convert back to UTC
        return saturday_8am.astimezone(timezone.utc)

