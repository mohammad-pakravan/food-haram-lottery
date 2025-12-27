from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.conf import settings
from django.utils.http import http_date
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .serializers import (
    PhoneNumberSerializer,
    OTPVerificationSerializer,
    UserProfileSerializer,
    TokenResponseSerializer
)
from .services import OTPService, KavehNegarService

User = get_user_model()


def set_jwt_cookies(response, refresh_token):
    """
    Helper function to set JWT tokens in HTTP-only cookies
    """
    access_token = refresh_token.access_token
    
    # Set access token cookie
    response.set_cookie(
        key=settings.COOKIE_ACCESS_TOKEN_NAME,
        value=str(access_token),
        max_age=int(settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds()),
        path='/',
        domain=None,
        secure=settings.COOKIE_SECURE,
        httponly=settings.COOKIE_HTTPONLY,
        samesite=settings.COOKIE_SAMESITE,
    )
    
    # Set refresh token cookie
    response.set_cookie(
        key=settings.COOKIE_REFRESH_TOKEN_NAME,
        value=str(refresh_token),
        max_age=int(settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds()),
        path='/',
        domain=None,
        secure=settings.COOKIE_SECURE,
        httponly=settings.COOKIE_HTTPONLY,
        samesite=settings.COOKIE_SAMESITE,
    )
    
    return response


def clear_jwt_cookies(response):
    """
    Helper function to clear JWT cookies (for logout)
    """
    response.set_cookie(
        key=settings.COOKIE_ACCESS_TOKEN_NAME,
        value='',
        max_age=0,
        path='/',
        domain=None,
        secure=settings.COOKIE_SECURE,
        httponly=settings.COOKIE_HTTPONLY,
        samesite=settings.COOKIE_SAMESITE,
    )
    
    response.set_cookie(
        key=settings.COOKIE_REFRESH_TOKEN_NAME,
        value='',
        max_age=0,
        path='/',
        domain=None,
        secure=settings.COOKIE_SECURE,
        httponly=settings.COOKIE_HTTPONLY,
        samesite=settings.COOKIE_SAMESITE,
    )
    
    return response


class RequestOTPView(APIView):
    """
    API endpoint to request OTP code
    
    این endpoint برای درخواست کد OTP استفاده می‌شود. کد OTP از طریق SMS به شماره تلفن ارسال می‌شود.
    """
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_description="درخواست کد OTP برای ثبت نام یا ورود. کد OTP از طریق SMS ارسال می‌شود.",
        request_body=PhoneNumberSerializer,
        responses={
            200: openapi.Response(
                description="کد OTP با موفقیت ارسال شد",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING, description='پیام موفقیت'),
                        'expires_in_minutes': openapi.Schema(type=openapi.TYPE_INTEGER, description='زمان انقضای کد به دقیقه'),
                    }
                )
            ),
            400: openapi.Response(description="خطا در درخواست"),
            404: openapi.Response(description="کاربر یافت نشد (برای login)"),
            429: openapi.Response(description="تعداد درخواست‌ها بیش از حد مجاز"),
            500: openapi.Response(description="خطای سرور"),
        },
        tags=['Authentication']
    )
    def post(self, request):
        serializer = PhoneNumberSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        phone_number = serializer.validated_data['phone_number']
        purpose = serializer.validated_data['purpose']
        
        # For login, check if user exists
        if purpose == 'login':
            if not User.objects.filter(phone_number=phone_number).exists():
                return Response(
                    {'error': 'User with this phone number does not exist'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # For register, check if user already exists
        if purpose == 'register':
            if User.objects.filter(phone_number=phone_number).exists():
                return Response(
                    {'error': 'User with this phone number already exists'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        try:
            # Generate and create OTP
            otp_code, otp_instance = OTPService.create_otp(phone_number, purpose)
            
            # Send OTP via SMS
            try:
                KavehNegarService.send_otp(phone_number, otp_code)
            except Exception as e:
                # Log error only in DEBUG mode
                if settings.DEBUG:
                    import traceback
                    print(f"KavehNegar error: {str(e)}")
                    print(traceback.format_exc())
                return Response(
                    {
                        'error': 'Failed to send OTP. Please try again later.',
                        'detail': str(e) if settings.DEBUG else None
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            expires_in = (otp_instance.expires_at - timezone.now()).total_seconds() / 60
            
            return Response(
                {
                    'message': 'OTP code has been sent to your phone number',
                    'expires_in_minutes': int(expires_in)
                },
                status=status.HTTP_200_OK
            )
            
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        except Exception as e:
            # Log error only in DEBUG mode
            if settings.DEBUG:
                import traceback
                print(f"Error in RequestOTPView: {str(e)}")
                print(traceback.format_exc())
            return Response(
                {'error': 'An error occurred. Please try again later.', 'detail': str(e) if settings.DEBUG else None},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class VerifyOTPView(APIView):
    """
    API endpoint to verify OTP and authenticate user
    
    این endpoint برای تایید کد OTP و دریافت JWT token استفاده می‌شود.
    در صورت ثبت نام، کاربر جدید ایجاد می‌شود و در صورت ورود، کاربر احراز هویت می‌شود.
    """
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_description="تایید کد OTP و دریافت JWT token. برای ثبت نام کاربر جدید ایجاد می‌شود و برای ورود کاربر احراز هویت می‌شود.",
        request_body=OTPVerificationSerializer,
        responses={
            200: openapi.Response(
                description="ورود موفقیت‌آمیز",
                schema=TokenResponseSerializer
            ),
            201: openapi.Response(
                description="ثبت نام موفقیت‌آمیز",
                schema=TokenResponseSerializer
            ),
            400: openapi.Response(description="کد OTP نامعتبر یا منقضی شده"),
            404: openapi.Response(description="کاربر یافت نشد"),
        },
        tags=['Authentication']
    )
    def post(self, request):
        serializer = OTPVerificationSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        phone_number = serializer.validated_data['phone_number']
        code = serializer.validated_data['code']
        purpose = serializer.validated_data['purpose']
        
        # Verify OTP
        otp_instance = OTPService.verify_otp(phone_number, code, purpose)
        
        if not otp_instance:
            return Response(
                {'error': 'Invalid or expired OTP code'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Handle registration
        if purpose == 'register':
            # Create new user
            user = User.objects.create_user(
                phone_number=phone_number,
                is_phone_verified=True
            )
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            user_serializer = UserProfileSerializer(user)
            
            # Create response
            response = Response(
                {
                    'message': 'User registered successfully',
                    'user': user_serializer.data
                },
                status=status.HTTP_201_CREATED
            )
            
            # Set tokens in HTTP-only cookies
            set_jwt_cookies(response, refresh)
            
            return response
        
        # Handle login
        elif purpose == 'login':
            try:
                user = User.objects.get(phone_number=phone_number)
                
                # Update phone verification status if not already verified
                if not user.is_phone_verified:
                    user.is_phone_verified = True
                    user.save()
                
                # Generate JWT tokens
                refresh = RefreshToken.for_user(user)
                
                user_serializer = UserProfileSerializer(user)
                
                # Create response
                response = Response(
                    {
                        'message': 'Login successful',
                        'user': user_serializer.data
                    },
                    status=status.HTTP_200_OK
                )
                
                # Set tokens in HTTP-only cookies
                set_jwt_cookies(response, refresh)
                
                return response
            except User.DoesNotExist:
                return Response(
                    {'error': 'User not found'},
                    status=status.HTTP_404_NOT_FOUND
                )


class LogoutView(APIView):
    """
    API endpoint to logout user
    Clears JWT cookies
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="خروج کاربر و پاک کردن JWT tokens از cookies",
        responses={
            200: openapi.Response(
                description="خروج موفقیت‌آمیز",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING, description='پیام موفقیت'),
                    }
                )
            ),
            401: openapi.Response(description="نیاز به احراز هویت"),
        },
        security=[{'Bearer': []}],
        tags=['Authentication']
    )
    def post(self, request):
        """
        Logout user by clearing JWT cookies
        """
        response = Response(
            {'message': 'Logged out successfully'},
            status=status.HTTP_200_OK
        )
        
        # Clear JWT cookies
        clear_jwt_cookies(response)
        
        return response


class RefreshTokenView(APIView):
    """
    API endpoint to refresh access token
    """
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_description="تازه‌سازی access token با استفاده از refresh token از cookie",
        responses={
            200: openapi.Response(
                description="Token با موفقیت تازه‌سازی شد",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING, description='پیام موفقیت'),
                    }
                )
            ),
            401: openapi.Response(description="Refresh token نامعتبر"),
        },
        tags=['Authentication']
    )
    def post(self, request):
        """
        Refresh access token using refresh token from cookie
        """
        refresh_token = request.COOKIES.get(settings.COOKIE_REFRESH_TOKEN_NAME)
        
        if not refresh_token:
            return Response(
                {'error': 'Refresh token not found'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        try:
            refresh = RefreshToken(refresh_token)
            access_token = refresh.access_token
            
            # Create response
            response = Response(
                {'message': 'Token refreshed successfully'},
                status=status.HTTP_200_OK
            )
            
            # Update access token cookie
            response.set_cookie(
                key=settings.COOKIE_ACCESS_TOKEN_NAME,
                value=str(access_token),
                max_age=int(settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds()),
                path='/',
                domain=None,
                secure=settings.COOKIE_SECURE,
                httponly=settings.COOKIE_HTTPONLY,
                samesite=settings.COOKIE_SAMESITE,
            )
            
            return response
            
        except Exception as e:
            return Response(
                {'error': 'Invalid refresh token'},
                status=status.HTTP_401_UNAUTHORIZED
            )


class UserProfileView(APIView):
    """
    API endpoint to view and update user profile
    
    این endpoint برای مشاهده و ویرایش پروفایل کاربر استفاده می‌شود.
    نیاز به احراز هویت دارد.
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="مشاهده پروفایل کاربر",
        responses={
            200: openapi.Response(
                description="پروفایل کاربر",
                schema=UserProfileSerializer
            ),
            401: openapi.Response(description="نیاز به احراز هویت"),
        },
        security=[{'Bearer': []}],
        tags=['User Profile']
    )
    def get(self, request):
        """
        Get user profile
        """
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        operation_description="ویرایش پروفایل کاربر",
        request_body=UserProfileSerializer,
        responses={
            200: openapi.Response(
                description="پروفایل به‌روزرسانی شد",
                schema=UserProfileSerializer
            ),
            400: openapi.Response(description="خطا در داده‌های ارسالی"),
            401: openapi.Response(description="نیاز به احراز هویت"),
        },
        security=[{'Bearer': []}],
        tags=['User Profile']
    )
    def patch(self, request):
        """
        Update user profile (currently only phone_verified can be updated)
        """
        serializer = UserProfileSerializer(
            request.user,
            data=request.data,
            partial=True
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

