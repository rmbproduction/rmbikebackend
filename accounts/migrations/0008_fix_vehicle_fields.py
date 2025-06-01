from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0007_alter_userprofile_manufacturer_and_more'),
    ]

    operations = [
        migrations.RunSQL(
            # Drop any existing foreign key constraints if they exist
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.table_constraints 
                    WHERE constraint_name LIKE 'accounts_userprofile_vehicle_name%'
                ) THEN
                    ALTER TABLE accounts_userprofile DROP CONSTRAINT IF EXISTS accounts_userprofile_vehicle_name_id_fkey;
                END IF;
                
                IF EXISTS (
                    SELECT 1 FROM information_schema.table_constraints 
                    WHERE constraint_name LIKE 'accounts_userprofile_vehicle_type%'
                ) THEN
                    ALTER TABLE accounts_userprofile DROP CONSTRAINT IF EXISTS accounts_userprofile_vehicle_type_id_fkey;
                END IF;
                
                IF EXISTS (
                    SELECT 1 FROM information_schema.table_constraints 
                    WHERE constraint_name LIKE 'accounts_userprofile_manufacturer%'
                ) THEN
                    ALTER TABLE accounts_userprofile DROP CONSTRAINT IF EXISTS accounts_userprofile_manufacturer_id_fkey;
                END IF;
            END $$;
            """,
            # No reverse SQL needed as we're fixing a broken state
            "SELECT 1;"
        ),
        migrations.RunSQL(
            # Ensure columns exist and are of correct type
            """
            DO $$
            BEGIN
                -- Fix vehicle_name column
                IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'accounts_userprofile' AND column_name = 'vehicle_name_id') THEN
                    ALTER TABLE accounts_userprofile RENAME COLUMN vehicle_name_id TO vehicle_name;
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'accounts_userprofile' AND column_name = 'vehicle_name') THEN
                    ALTER TABLE accounts_userprofile ADD COLUMN vehicle_name integer NULL;
                ELSE
                    ALTER TABLE accounts_userprofile ALTER COLUMN vehicle_name TYPE integer USING vehicle_name::integer;
                END IF;

                -- Fix vehicle_type column
                IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'accounts_userprofile' AND column_name = 'vehicle_type_id') THEN
                    ALTER TABLE accounts_userprofile RENAME COLUMN vehicle_type_id TO vehicle_type;
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'accounts_userprofile' AND column_name = 'vehicle_type') THEN
                    ALTER TABLE accounts_userprofile ADD COLUMN vehicle_type integer NULL;
                ELSE
                    ALTER TABLE accounts_userprofile ALTER COLUMN vehicle_type TYPE integer USING vehicle_type::integer;
                END IF;

                -- Fix manufacturer column
                IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'accounts_userprofile' AND column_name = 'manufacturer_id') THEN
                    ALTER TABLE accounts_userprofile RENAME COLUMN manufacturer_id TO manufacturer;
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'accounts_userprofile' AND column_name = 'manufacturer') THEN
                    ALTER TABLE accounts_userprofile ADD COLUMN manufacturer integer NULL;
                ELSE
                    ALTER TABLE accounts_userprofile ALTER COLUMN manufacturer TYPE integer USING manufacturer::integer;
                END IF;
            END $$;
            """,
            # No reverse SQL needed as we're fixing a broken state
            "SELECT 1;"
        ),
    ] 