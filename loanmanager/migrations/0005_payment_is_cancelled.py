# Generated by Django 4.1 on 2025-03-05 03:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('loanmanager', '0004_reddituser_lender_unpaid_loan_balance_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='is_cancelled',
            field=models.BooleanField(default=False),
        ),
    ]
