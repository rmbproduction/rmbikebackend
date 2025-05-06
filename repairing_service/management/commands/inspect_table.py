from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Inspect ServiceCategory table structure'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # Get all columns from table
            cursor.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = 'repairing_service_servicecategory'
                ORDER BY ordinal_position;
            """)
            columns = cursor.fetchall()

            # Get primary key information
            cursor.execute("""
                SELECT con.conname, pg_get_constraintdef(con.oid)
                FROM pg_constraint con
                INNER JOIN pg_class rel ON rel.oid = con.conrelid
                INNER JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
                WHERE rel.relname = 'repairing_service_servicecategory'
                AND con.contype = 'p';
            """)
            primary_keys = cursor.fetchall()

            # Print results
            self.stdout.write(self.style.SUCCESS('Table Columns:'))
            for column in columns:
                self.stdout.write(f"  {column[0]}: {column[1]}, nullable: {column[2]}, default: {column[3]}")

            self.stdout.write(self.style.SUCCESS('\nPrimary Keys:'))
            for pk in primary_keys:
                self.stdout.write(f"  {pk[0]}: {pk[1]}") 