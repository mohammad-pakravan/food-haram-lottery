from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.lottery.services import LotteryService, KavehNegarLotteryService
from apps.lottery.models import Ticket
from django.conf import settings


class Command(BaseCommand):
    help = 'Run lottery and select winners from current week'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            help='Number of winners to select (default: from settings)',
        )

    def handle(self, *args, **options):
        self.stdout.write('Starting lottery...')
        
        # Get tickets for current week
        tickets = LotteryService.get_current_week_tickets()
        tickets_count = tickets.count()
        
        self.stdout.write(f'Found {tickets_count} pending tickets for current week')
        
        if tickets_count == 0:
            self.stdout.write(self.style.WARNING('No tickets found for current week'))
            return
        
        # Get winner count
        winner_count = options.get('count') or settings.LOTTERY_WINNERS_COUNT
        
        if tickets_count < winner_count:
            self.stdout.write(
                self.style.WARNING(
                    f'Only {tickets_count} tickets available, selecting {tickets_count} winners instead of {winner_count}'
                )
            )
            winner_count = tickets_count
        
        # Select winners
        self.stdout.write(f'Selecting {winner_count} winners...')
        winners = LotteryService.select_winners(winner_count)
        
        self.stdout.write(self.style.SUCCESS(f'Selected {winners.count()} winners'))
        
        # Send SMS to winners
        self.stdout.write('Sending SMS to winners...')
        success_count = 0
        fail_count = 0
        
        for winner in winners:
            try:
                KavehNegarLotteryService.send_winner_sms(
                    winner.user.phone_number,
                    winner.ticket_number
                )
                success_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'SMS sent to {winner.user.phone_number} (Ticket: {winner.ticket_number})'
                    )
                )
            except Exception as e:
                fail_count += 1
                self.stdout.write(
                    self.style.ERROR(
                        f'Failed to send SMS to {winner.user.phone_number}: {str(e)}'
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Lottery completed! Winners: {success_count}, Failed SMS: {fail_count}'
            )
        )


