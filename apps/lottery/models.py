from django.db import models
from django.contrib.auth import get_user_model
import random
import string

User = get_user_model()


class Ticket(models.Model):
    """
    Model for lottery tickets
    """
    STATUS_CHOICES = [
        ('pending', 'در انتظار'),
        ('active', 'فعال'),
        ('won', 'برنده'),
        ('expired', 'منقضی شده'),
        ('cancelled', 'لغو شده'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='tickets',
        help_text="کاربر صاحب بلیط"
    )
    ticket_number = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        help_text="شماره ژتون (رندوم از سمت سرور)"
    )
    national_id = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        help_text="کد ملی"
    )
    full_name = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        help_text="نام و نام خانوادگی"
    )
    received_date = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="تاریخ دریافت"
    )
    selected_period = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="وعده انتخابی"
    )
    quantity = models.IntegerField(
        null=True,
        blank=True,
        help_text="تعداد"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True,
        help_text="وضعیت تیکت"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'lottery_tickets'
        verbose_name = 'Ticket'
        verbose_name_plural = 'Tickets'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['ticket_number']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"Ticket {self.ticket_number} - {self.user.phone_number}"
    
    @staticmethod
    def generate_ticket_number():
        """
        Generate a random unique ticket number
        Format: Random alphanumeric string
        """
        while True:
            # Generate random ticket number (10 characters)
            ticket_number = ''.join(
                random.choices(string.ascii_uppercase + string.digits, k=10)
            )
            
            # Check if it already exists
            if not Ticket.objects.filter(ticket_number=ticket_number).exists():
                return ticket_number
    
    def save(self, *args, **kwargs):
        """
        Override save to auto-generate ticket_number if not provided
        """
        if not self.ticket_number:
            self.ticket_number = self.generate_ticket_number()
        super().save(*args, **kwargs)

