# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lottery', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='ticket',
            name='national_id',
            field=models.CharField(blank=True, help_text='کد ملی', max_length=10, null=True),
        ),
        migrations.AddField(
            model_name='ticket',
            name='full_name',
            field=models.CharField(blank=True, help_text='نام و نام خانوادگی', max_length=200, null=True),
        ),
    ]

