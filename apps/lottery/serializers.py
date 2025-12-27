from rest_framework import serializers
from .models import Ticket


class TicketSerializer(serializers.ModelSerializer):
    """
    Serializer for Ticket model
    """
    class Meta:
        model = Ticket
        fields = [
            'id',
            'ticket_number',
            'national_id',
            'full_name',
            'received_date',
            'selected_period',
            'quantity',
            'status',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'id',
            'ticket_number',
            'status',
            'created_at',
            'updated_at'
        ]


class TicketCreateSerializer(serializers.Serializer):
    """
    Serializer for creating a ticket (no fields needed, user comes from auth)
    """
    pass


class WinnerInfoSerializer(serializers.Serializer):
    """
    Serializer for winner to complete their information
    """
    full_name = serializers.CharField(
        max_length=200,
        required=True,
        help_text="نام و نام خانوادگی"
    )
    national_id = serializers.CharField(
        max_length=10,
        required=True,
        help_text="کد ملی"
    )
    received_date = serializers.CharField(
        max_length=100,
        required=True,
        help_text="تاریخ دریافت"
    )
    selected_period = serializers.CharField(
        max_length=100,
        required=True,
        help_text="وعده انتخابی"
    )
    quantity = serializers.IntegerField(
        required=True,
        min_value=1,
        max_value=3,
        help_text="تعداد (بین 1 تا 3)"
    )
    
    def validate_national_id(self, value):
        """
        Validate national ID format
        """
        cleaned = ''.join(filter(str.isdigit, value))
        
        if len(cleaned) != 10:
            raise serializers.ValidationError("کد ملی باید 10 رقم باشد")
        
        return cleaned
