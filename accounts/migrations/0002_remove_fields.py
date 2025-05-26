from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            DO $$
            BEGIN
                -- Drop columns if they exist
                IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'accounts_userprofile' AND column_name = 'preferredlocation') THEN
                    ALTER TABLE accounts_userprofile DROP COLUMN preferredlocation;
                END IF;
                
                IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'accounts_userprofile' AND column_name = 'latitude') THEN
                    ALTER TABLE accounts_userprofile DROP COLUMN latitude;
                END IF;
                
                IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'accounts_userprofile' AND column_name = 'longitude') THEN
                    ALTER TABLE accounts_userprofile DROP COLUMN longitude;
                END IF;
            END $$;
            """,
            reverse_sql="""
            DO $$
            BEGIN
                -- Add columns back if they don't exist
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'accounts_userprofile' AND column_name = 'preferredlocation') THEN
                    ALTER TABLE accounts_userprofile ADD COLUMN preferredlocation varchar(255);
                END IF;
                
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'accounts_userprofile' AND column_name = 'latitude') THEN
                    ALTER TABLE accounts_userprofile ADD COLUMN latitude double precision;
                END IF;
                
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'accounts_userprofile' AND column_name = 'longitude') THEN
                    ALTER TABLE accounts_userprofile ADD COLUMN longitude double precision;
                END IF;
            END $$;
            """
        )
    ] 