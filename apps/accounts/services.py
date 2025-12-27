import random
import string
import hashlib
import requests
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password
from .models import OTPCode, User


class OTPService:
    """
    Service for OTP code generation and verification
    """
    
    @staticmethod
    def generate_otp_code(length=None):
        """
        Generate a random OTP code
        """
        if length is None:
            length = settings.OTP_CODE_LENGTH
        
        return ''.join(random.choices(string.digits, k=length))
    
    @staticmethod
    def create_otp(phone_number, purpose):
        """
        Create and save an OTP code for the given phone number
        Returns the plain OTP code (to be sent via SMS) and the OTPCode instance
        """
        # Check rate limiting
        if not OTPService._check_rate_limit(phone_number):
            raise ValueError("Too many OTP requests. Please try again later.")
        
        # Generate OTP code
        otp_code = OTPService.generate_otp_code()
        
        # Hash the code
        code_hash = make_password(otp_code)
        
        # Calculate expiry time
        expires_at = timezone.now() + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)
        
        # Create OTP record
        otp_instance = OTPCode.objects.create(
            phone_number=phone_number,
            code_hash=code_hash,
            purpose=purpose,
            expires_at=expires_at
        )
        
        return otp_code, otp_instance
    
    @staticmethod
    def verify_otp(phone_number, code, purpose):
        """
        Verify an OTP code
        Returns the OTPCode instance if valid, None otherwise
        """
        # Get the most recent unused OTP for this phone number and purpose
        otp_instance = OTPCode.objects.filter(
            phone_number=phone_number,
            purpose=purpose,
            is_used=False
        ).order_by('-created_at').first()
        
        if not otp_instance:
            return None
        
        # Check if expired
        if otp_instance.is_expired():
            return None
        
        # Verify the code
        if check_password(code, otp_instance.code_hash):
            # Mark as used
            otp_instance.is_used = True
            otp_instance.save()
            return otp_instance
        
        return None
    
    @staticmethod
    def _check_rate_limit(phone_number):
        """
        Check if the phone number has exceeded the rate limit
        Returns True if allowed, False if rate limited
        """
        limit_minutes = settings.OTP_RATE_LIMIT_MINUTES
        limit_count = settings.OTP_RATE_LIMIT_COUNT
        
        since = timezone.now() - timedelta(minutes=limit_minutes)
        
        recent_otps = OTPCode.objects.filter(
            phone_number=phone_number,
            created_at__gte=since
        ).count()
        
        return recent_otps < limit_count
    
    @staticmethod
    def cleanup_expired_otps():
        """
        Clean up expired OTP codes (can be run as a periodic task)
        """
        expired_count = OTPCode.objects.filter(
            expires_at__lt=timezone.now()
        ).delete()[0]
        
        return expired_count


class KavehNegarService:
    """
    Service for sending SMS via KavehNegar API
    """
    
    @staticmethod
    def send_otp_sms(phone_number, otp_code, template_name=None):
        """
        Send OTP code via SMS using KavehNegar API
        Returns True if successful, False otherwise
        """
        api_key = settings.KAVEHNEGAR_API_KEY
        template = template_name or settings.KAVEHNEGAR_OTP_TEMPLATE
        
        if not api_key:
            raise ValueError("KAVEHNEGAR_API_KEY is not configured")
        
        if not template:
            raise ValueError("KAVEHNEGAR_OTP_TEMPLATE is not configured")
        
        url = f"{settings.KAVEHNEGAR_API_URL}/{api_key}/verify/lookup.json"
        
        data = {
            'template': template,
            'receptor': phone_number,
            'token': otp_code
        }
        
        try:
            response = requests.post(url, data=data, timeout=10)
            
            # Check HTTP status
            if response.status_code != 200:
                error_msg = f"KavehNegar API returned status {response.status_code}"
                try:
                    error_data = response.json()
                    error_message = error_data.get('return', {}).get('message', 'Unknown error')
                    error_status = error_data.get('return', {}).get('status', response.status_code)
                    error_msg = f"KavehNegar API error (status {error_status}): {error_message}"
                except:
                    error_msg += f": {response.text}"
                raise Exception(error_msg)
            
            result = response.json()
            
            # KavehNegar API response structure:
            # {
            #   "return": {
            #     "status": 200,
            #     "message": "..."
            #   },
            #   "entries": [...]
            # }
            return_status = result.get('return', {}).get('status')
            
            if return_status == 200:
                return True
            else:
                error_message = result.get('return', {}).get('message', 'Unknown error')
                raise Exception(f"KavehNegar API error: {error_message}")
                
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to send SMS via KavehNegar: {str(e)}")
        except Exception as e:
            # Re-raise with more context
            raise Exception(f"KavehNegar service error: {str(e)}")
    
    @staticmethod
    def send_otp(phone_number, otp_code):
        """
        Convenience method to send OTP
        """
        return KavehNegarService.send_otp_sms(phone_number, otp_code)

