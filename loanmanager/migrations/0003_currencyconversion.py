# Generated by Django 4.1 on 2024-06-05 23:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('loanmanager', '0002_reddituser_is_mod'),
    ]

    operations = [
        migrations.CreateModel(
            name='CurrencyConversion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('currency', models.CharField(max_length=10, unique=True)),
                ('conversion_rate_to_usd', models.DecimalField(decimal_places=2, max_digits=10)),
            ],
        ),
    ]