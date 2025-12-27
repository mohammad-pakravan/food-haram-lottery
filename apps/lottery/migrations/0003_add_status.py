# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lottery', '0002_add_national_id_and_full_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='ticket',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending', 'در انتظار'),
                    ('active', 'فعال'),
                    ('won', 'برنده'),
                    ('expired', 'منقضی شده'),
                    ('cancelled', 'لغو شده'),
                ],
                db_index=True,
                default='pending',
                help_text='وضعیت تیکت',
                max_length=20
            ),
        ),
        migrations.AddIndex(
            model_name='ticket',
            index=models.Index(fields=['status'], name='lottery_tic_status_idx'),
        ),
    ]

