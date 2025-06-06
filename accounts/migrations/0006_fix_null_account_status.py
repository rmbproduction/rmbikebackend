from django.db import migrations

def fix_null_account_status(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    # Update all users with NULL account_status to 'unverified'
    User.objects.filter(account_status__isnull=True).update(account_status='unverified')

class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0005_user_account_status_user_last_verification_sent_and_more'),
    ]

    operations = [
        migrations.RunPython(fix_null_account_status, reverse_code=migrations.RunPython.noop),
    ] 