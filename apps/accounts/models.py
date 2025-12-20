from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils import timezone


class UserManager(BaseUserManager):
    """
    Custom user manager where phone_number is the unique identifier
    """
    
    def create_user(self, phone_number, password=None, **extra_fields):
        """
        Create and save a regular user with the given phone_number and password.
        """
        if not phone_number:
            raise ValueError('The phone_number must be set')
        
        user = self.model(phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, phone_number, password=None, **extra_fields):
        """
        Create and save a superuser with the given phone_number and password.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_phone_verified', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(phone_number, password, **extra_fields)


class User(AbstractUser):
    """
    Custom User model with phone_number as primary identifier
    """
    username = None  # Remove username field
    email = None  # Remove email field (optional, can keep if needed)
    
    phone_number = models.CharField(
        max_length=15,
        unique=True,
        db_index=True,
        help_text="User's phone number"
    )
    is_phone_verified = models.BooleanField(
        default=False,
        help_text="Whether the phone number has been verified"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = []
    
    objects = UserManager()
    
    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        indexes = [
            models.Index(fields=['phone_number']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return self.phone_number


class OTPCode(models.Model):
    """
    Model to store OTP codes for phone verification
    """
    PURPOSE_CHOICES = [
        ('register', 'Register'),
        ('login', 'Login'),
    ]
    
    phone_number = models.CharField(max_length=15, db_index=True)
    code_hash = models.CharField(max_length=255)  # Hashed OTP code
    purpose = models.CharField(max_length=10, choices=PURPOSE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'otp_codes'
        verbose_name = 'OTP Code'
        verbose_name_plural = 'OTP Codes'
        indexes = [
            models.Index(fields=['phone_number', 'created_at']),
            models.Index(fields=['phone_number', 'purpose', 'is_used']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"OTP for {self.phone_number} - {self.purpose}"
    
    def is_expired(self):
        """Check if OTP code has expired"""
        return timezone.now() > self.expires_at
    
    def is_valid(self):
        """Check if OTP code is valid (not used and not expired)"""
        return not self.is_used and not self.is_expired()

