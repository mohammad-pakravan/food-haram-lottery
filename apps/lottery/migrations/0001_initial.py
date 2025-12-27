# Generated manually

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Ticket',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ticket_number', models.CharField(db_index=True, help_text='شماره ژتون (رندوم از سمت سرور)', max_length=20, unique=True)),
                ('national_id', models.CharField(blank=True, help_text='کد ملی', max_length=10, null=True)),
                ('full_name', models.CharField(blank=True, help_text='نام و نام خانوادگی', max_length=200, null=True)),
                ('received_date', models.CharField(blank=True, help_text='تاریخ دریافت', max_length=100, null=True)),
                ('selected_period', models.CharField(blank=True, help_text='وعده انتخابی', max_length=100, null=True)),
                ('quantity', models.IntegerField(blank=True, help_text='تعداد', null=True)),
                ('status', models.CharField(choices=[('pending', 'در انتظار'), ('active', 'فعال'), ('won', 'برنده'), ('expired', 'منقضی شده'), ('cancelled', 'لغو شده')], db_index=True, default='pending', help_text='وضعیت تیکت', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(help_text='کاربر صاحب بلیط', on_delete=django.db.models.deletion.CASCADE, related_name='tickets', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Ticket',
                'verbose_name_plural': 'Tickets',
                'db_table': 'lottery_tickets',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='ticket',
            index=models.Index(fields=['ticket_number'], name='lottery_tic_ticket__idx'),
        ),
        migrations.AddIndex(
            model_name='ticket',
            index=models.Index(fields=['user', 'created_at'], name='lottery_tic_user_id_created_idx'),
        ),
        migrations.AddIndex(
            model_name='ticket',
            index=models.Index(fields=['status'], name='lottery_tic_status_idx'),
        ),
    ]

