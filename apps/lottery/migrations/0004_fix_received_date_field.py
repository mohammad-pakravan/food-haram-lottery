# Generated manually to fix received_date field type
# This migration converts received_date from DateField to CharField in the database

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lottery', '0003_add_status'),
    ]

    operations = [
        # First, convert the database column from date to varchar
        migrations.RunSQL(
            sql="ALTER TABLE lottery_tickets ALTER COLUMN received_date TYPE VARCHAR(100) USING received_date::text;",
            reverse_sql="ALTER TABLE lottery_tickets ALTER COLUMN received_date TYPE DATE USING received_date::date;",
        ),
        # Then update the Django model field definition
        migrations.AlterField(
            model_name='ticket',
            name='received_date',
            field=models.CharField(blank=True, help_text='تاریخ دریافت', max_length=100, null=True),
        ),
    ]
