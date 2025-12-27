from django.urls import path
from .views import (
    ParticipateLotteryView,
    CompleteWinnerInfoView,
    UserTicketsHistoryView,
    CurrentWeekWinnersView
)
from .admin_views import run_lottery_manual

app_name = 'lottery'

urlpatterns = [
    path('participate/', ParticipateLotteryView.as_view(), name='participate'),
    path('complete-winner-info/', CompleteWinnerInfoView.as_view(), name='complete-winner-info'),
    path('my-tickets/', UserTicketsHistoryView.as_view(), name='user-tickets-history'),
    path('current-week-winners/', CurrentWeekWinnersView.as_view(), name='current-week-winners'),
    path('admin/run-lottery/', run_lottery_manual, name='run-lottery-manual'),
]

