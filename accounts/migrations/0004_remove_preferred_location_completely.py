from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0003_fix_preferred_location'),
    ]

    operations = [
        migrations.RunSQL(
            # Forward SQL - Remove the column and any related constraints
            sql="""
            DO $$
            BEGIN
                -- First make the column nullable if it exists and isn't already
                BEGIN
                    ALTER TABLE accounts_userprofile 
                    ALTER COLUMN preferredlocation DROP NOT NULL;
                EXCEPTION
                    WHEN undefined_column THEN
                        NULL;
                END;

                -- Then drop the column if it exists
                BEGIN
                    ALTER TABLE accounts_userprofile 
                    DROP COLUMN IF EXISTS preferredlocation;
                EXCEPTION
                    WHEN undefined_column THEN
                        NULL;
                END;

                -- Clean up any related constraints or indexes
                -- This will catch any remaining references to the column
                DO $cleanup$
                BEGIN
                    EXECUTE (
                        SELECT string_agg('DROP CONSTRAINT ' || quote_ident(conname), '; ')
                        FROM pg_constraint
                        WHERE conrelid = 'accounts_userprofile'::regclass
                        AND conname LIKE '%preferredlocation%'
                    );
                    
                    EXECUTE (
                        SELECT string_agg('DROP INDEX ' || quote_ident(indexname), '; ')
                        FROM pg_indexes
                        WHERE tablename = 'accounts_userprofile'
                        AND indexname LIKE '%preferredlocation%'
                    );
                EXCEPTION
                    WHEN OTHERS THEN
                        NULL;
                END $cleanup$;
            END $$;
            """,
            # Reverse SQL - We don't want to add it back
            reverse_sql="""
            DO $$
            BEGIN
                -- No reverse operation - we don't want to add the field back
                NULL;
            END $$;
            """
        )
    ] 