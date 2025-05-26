from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            # Forward SQL - Drop columns if they exist
            sql="""
            DO $$
            BEGIN
                ALTER TABLE accounts_userprofile 
                DROP COLUMN IF EXISTS preferredlocation,
                DROP COLUMN IF EXISTS latitude,
                DROP COLUMN IF EXISTS longitude;
            END $$;
            """,
            # Reverse SQL - Add columns back
            reverse_sql="""
            DO $$
            BEGIN
                ALTER TABLE accounts_userprofile 
                ADD COLUMN IF NOT EXISTS preferredlocation varchar(255) NULL,
                ADD COLUMN IF NOT EXISTS latitude double precision NULL,
                ADD COLUMN IF NOT EXISTS longitude double precision NULL;
            END $$;
            """
        )
    ] 