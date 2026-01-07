from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from .models import OTPCode

User = get_user_model()


class PhoneNumberSerializer(serializers.Serializer):
    """
    Serializer for requesting OTP
    """
    phone_number = serializers.CharField(
        max_length=15,
        help_text="Phone number to send OTP to"
    )
    purpose = serializers.ChoiceField(
        choices=['register', 'login'],
        help_text="Purpose of OTP: 'register' for registration, 'login' for login"
    )
    
    def validate_phone_number(self, value):
        """
        Validate phone number format (basic validation)
        """
        # Remove any non-digit characters
        cleaned = ''.join(filter(str.isdigit, value))
        
        if len(cleaned) < 10:
            raise serializers.ValidationError("Phone number must be at least 10 digits")
        
        return cleaned


class OTPVerificationSerializer(serializers.Serializer):
    """
    Serializer for verifying OTP
    """
    phone_number = serializers.CharField(max_length=15)
    code = serializers.CharField(
        max_length=10,
        help_text="OTP code received via SMS"
    )
    purpose = serializers.ChoiceField(
        choices=['register', 'login'],
        help_text="Purpose of OTP: 'register' for registration, 'login' for login"
    )
    
    def validate_phone_number(self, value):
        """
        Validate phone number format
        """
        cleaned = ''.join(filter(str.isdigit, value))
        
        if len(cleaned) < 10:
            raise serializers.ValidationError("Phone number must be at least 10 digits")
        
        return cleaned
    
    def validate_code(self, value):
        """
        Validate OTP code format
        """
        if not value.isdigit():
            raise serializers.ValidationError("OTP code must contain only digits")
        
        return value


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for user profile
    """
    class Meta:
        model = User
        fields = ['id', 'phone_number', 'national_id', 'is_phone_verified', 'created_at', 'updated_at']
        read_only_fields = ['id', 'phone_number', 'is_phone_verified', 'created_at', 'updated_at']
    
    def validate_national_id(self, value):
        """
        Validate national ID format (10 digits)
        """
        if value:
            if not value.isdigit():
                raise serializers.ValidationError("کد ملی باید فقط شامل اعداد باشد")
            if len(value) != 10:
                raise serializers.ValidationError("کد ملی باید دقیقاً 10 رقم باشد")
        return value


class TokenResponseSerializer(serializers.Serializer):
    """
    Serializer for JWT token response
    """
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserProfileSerializer()

