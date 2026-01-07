from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.csrf import csrf_protect
from .services import LotteryService, KavehNegarLotteryService
from django.conf import settings


@staff_member_required
@csrf_protect
def run_lottery_manual(request):
    """
    Manual lottery execution from admin panel
    """
    try:
        # Get tickets for current week
        tickets = LotteryService.get_current_week_tickets()
        tickets_count = tickets.count()
        
        if tickets_count == 0:
            messages.warning(
                request,
                'هیچ تیکت pending برای هفته جاری یافت نشد'
            )
            return redirect('admin:lottery_ticket_changelist')
        
        # Select winners
        winners = LotteryService.select_winners()
        winner_count = winners.count()
        
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
            except Exception as e:
                fail_count += 1
                if settings.DEBUG:
                    print(f"Failed to send SMS to {winner.user.phone_number}: {str(e)}")
        
        messages.success(
            request,
            f'قرعه کشی با موفقیت انجام شد! تعداد برندگان: {winner_count}, پیامک ارسال شده: {success_count}, خطا در ارسال: {fail_count}'
        )
    except Exception as e:
        messages.error(
            request,
            f'خطا در اجرای قرعه کشی: {str(e)}'
        )
    
    return redirect('admin:lottery_ticket_changelist')


