# Generated by Django 5.0 on 2023-12-27 22:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('loanmanager', '0004_alter_commentsrepliedto_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='loan',
            name='amount_in_usd',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name='loan',
            name='is_cancelled',
            field=models.BooleanField(default=False),
        ),
    ]
