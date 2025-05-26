from django.db import migrations, models

def set_default_preferred_location(apps, schema_editor):
    UserProfile = apps.get_model('accounts', 'UserProfile')
    UserProfile.objects.filter(preferredLocation__isnull=True).update(preferredLocation='')

class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        # First, make the field nullable
        migrations.AlterField(
            model_name='userprofile',
            name='preferredLocation',
            field=models.CharField(max_length=255, null=True, blank=True),
        ),
        # Then set default values
        migrations.RunPython(set_default_preferred_location),
        # Finally, remove the fields
        migrations.RemoveField(
            model_name='userprofile',
            name='preferredLocation',
        ),
        migrations.RemoveField(
            model_name='userprofile',
            name='latitude',
        ),
        migrations.RemoveField(
            model_name='userprofile',
            name='longitude',
        ),
    ] 