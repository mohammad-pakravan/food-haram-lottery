from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.shortcuts import redirect
from django.contrib import messages
from .models import Ticket
from .services import LotteryService, KavehNegarLotteryService
from django.conf import settings


@admin.action(description='اجرای قرعه کشی برای تیکت‌های هفته جاری')
def run_lottery_action(modeladmin, request, queryset):
    """
    Admin action to run lottery manually
    """
    try:
        # Get tickets for current week
        tickets = LotteryService.get_current_week_tickets()
        tickets_count = tickets.count()
        
        if tickets_count == 0:
            modeladmin.message_user(
                request,
                'هیچ تیکت pending برای هفته جاری یافت نشد',
                level=messages.WARNING
            )
            return
        
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
        
        modeladmin.message_user(
            request,
            f'قرعه کشی با موفقیت انجام شد! تعداد برندگان: {winner_count}, پیامک ارسال شده: {success_count}, خطا در ارسال: {fail_count}',
            level=messages.SUCCESS
        )
    except Exception as e:
        modeladmin.message_user(
            request,
            f'خطا در اجرای قرعه کشی: {str(e)}',
            level=messages.ERROR
        )


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('ticket_number', 'user', 'full_name', 'national_id', 'status', 'received_date', 'selected_period', 'quantity', 'created_at')
    list_filter = ('status', 'selected_period', 'created_at')
    search_fields = ('ticket_number', 'user__phone_number', 'national_id', 'full_name')
    readonly_fields = ('ticket_number', 'created_at', 'updated_at')
    ordering = ('-created_at',)
    actions = [run_lottery_action]
    
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('user', 'ticket_number', 'status')
        }),
        ('اطلاعات شخصی', {
            'fields': ('full_name', 'national_id')
        }),
        ('اطلاعات قرعه کشی', {
            'fields': ('received_date', 'selected_period', 'quantity')
        }),
        ('اطلاعات زمانی', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def changelist_view(self, request, extra_context=None):
        """
        Add custom button to run lottery
        """
        from django.urls import reverse
        extra_context = extra_context or {}
        extra_context['lottery_url'] = reverse('lottery:run-lottery-manual')
        return super().changelist_view(request, extra_context=extra_context)

