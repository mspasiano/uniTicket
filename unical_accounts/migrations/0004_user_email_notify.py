# Generated by Django 2.2.1 on 2019-05-07 12:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('unical_accounts', '0003_auto_20190226_0838'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='email_notify',
            field=models.BooleanField(default=True, verbose_name='Notifiche mail'),
        ),
    ]
