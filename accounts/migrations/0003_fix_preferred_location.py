from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0002_alter_userprofile'),
    ]

    operations = [
        migrations.RunSQL(
            # Forward SQL - First make the column nullable, then drop it
            sql="""
            DO $$
            BEGIN
                -- First make the column nullable
                ALTER TABLE accounts_userprofile 
                ALTER COLUMN preferredlocation DROP NOT NULL;
                
                -- Then drop the column
                ALTER TABLE accounts_userprofile 
                DROP COLUMN IF EXISTS preferredlocation;
            EXCEPTION
                WHEN undefined_column THEN
                    -- Column doesn't exist, which is fine
                    NULL;
            END $$;
            """,
            # Reverse SQL - Add the column back as nullable
            reverse_sql="""
            DO $$
            BEGIN
                ALTER TABLE accounts_userprofile 
                ADD COLUMN IF NOT EXISTS preferredlocation varchar(255) NULL;
            END $$;
            """
        )
    ] 