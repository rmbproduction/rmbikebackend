from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Fixes the NOT NULL constraint on vehicle_name field in accounts_userprofile table'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting to fix vehicle_name constraint...'))
        
        with connection.cursor() as cursor:
            # Get table info
            cursor.execute("""
                SELECT column_name, is_nullable, data_type
                FROM information_schema.columns
                WHERE table_name = 'accounts_userprofile' AND column_name = 'vehicle_name_id';
            """)
            column_info = cursor.fetchone()
            
            if column_info:
                column_name, is_nullable, data_type = column_info
                self.stdout.write(f"Found column: {column_name}, Nullable: {is_nullable}, Type: {data_type}")
                
                if is_nullable == 'NO':
                    self.stdout.write(self.style.WARNING('Found NOT NULL constraint, dropping it...'))
                    
                    # Drop the NOT NULL constraint
                    cursor.execute("""
                        ALTER TABLE accounts_userprofile 
                        ALTER COLUMN vehicle_name_id DROP NOT NULL;
                    """)
                    
                    self.stdout.write(self.style.SUCCESS('Successfully dropped NOT NULL constraint on vehicle_name_id'))
                else:
                    self.stdout.write(self.style.SUCCESS('No constraint found, already nullable'))
            else:
                self.stdout.write(self.style.ERROR('Column vehicle_name_id not found in accounts_userprofile table')) 