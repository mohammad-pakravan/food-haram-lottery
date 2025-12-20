from django.urls import path
from .views import RequestOTPView, VerifyOTPView, LogoutView, RefreshTokenView, UserProfileView

app_name = 'accounts'

urlpatterns = [
    path('request-otp/', RequestOTPView.as_view(), name='request-otp'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('refresh-token/', RefreshTokenView.as_view(), name='refresh-token'),
    path('profile/', UserProfileView.as_view(), name='profile'),
]

