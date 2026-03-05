from django.db import migrations, models


def dismiss_old_notifications(apps, schema_editor):
    Loan = apps.get_model('loanmanager', 'Loan')
    # Dismiss all unpaid loans that are NOT from December 2025
    Loan.objects.filter(is_unpaid=True).exclude(
        creation_date__year=2025,
        creation_date__month=12
    ).update(notification_dismissed=True)


class Migration(migrations.Migration):

    dependencies = [
        ('loanmanager', '0005_payment_is_cancelled'),
    ]

    operations = [
        migrations.AddField(
            model_name='loan',
            name='notification_dismissed',
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(dismiss_old_notifications, migrations.RunPython.noop),
    ]
