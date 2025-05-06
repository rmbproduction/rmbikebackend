from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Fix all vehicle-related foreign key constraints in UserProfile table'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting to fix vehicle constraints...'))
        
        vehicle_fields = [
            'vehicle_name_id', 
            'vehicle_type_id', 
            'manufacturer_id'
        ]
        
        with connection.cursor() as cursor:
            for field in vehicle_fields:
                # First check if the constraint exists
                cursor.execute(f"""
                    SELECT column_name, is_nullable, data_type
                    FROM information_schema.columns
                    WHERE table_name = 'accounts_userprofile' AND column_name = '{field}';
                """)
                column_info = cursor.fetchone()
                
                if column_info:
                    column_name, is_nullable, data_type = column_info
                    self.stdout.write(f"Found column: {column_name}, Nullable: {is_nullable}, Type: {data_type}")
                    
                    if is_nullable == 'NO':
                        self.stdout.write(self.style.WARNING(f'Found NOT NULL constraint on {field}, dropping it...'))
                        
                        # Drop the NOT NULL constraint
                        cursor.execute(f"""
                            ALTER TABLE accounts_userprofile 
                            ALTER COLUMN {field} DROP NOT NULL;
                        """)
                        
                        self.stdout.write(self.style.SUCCESS(f'Successfully dropped NOT NULL constraint on {field}'))
                    else:
                        self.stdout.write(self.style.SUCCESS(f'Field {field} is already nullable, no action needed'))
                else:
                    self.stdout.write(self.style.ERROR(f'Column {field} not found in accounts_userprofile table'))
        
        # Also update default values for text fields
        text_fields = [
            'address', 'city', 'state', 'postal_code', 'phone', 'preferredLocation'
        ]
        
        for field in text_fields:
            try:
                with connection.cursor() as cursor:
                    # Check if the column has a default value
                    cursor.execute(f"""
                        SELECT column_default
                        FROM information_schema.columns
                        WHERE table_name = 'accounts_userprofile' AND column_name = '{field}';
                    """)
                    column_info = cursor.fetchone()
                    if column_info and column_info[0] is None:
                        self.stdout.write(self.style.WARNING(f'Setting default empty string for {field}...'))
                        cursor.execute(f"""
                            ALTER TABLE accounts_userprofile
                            ALTER COLUMN {field} SET DEFAULT '';
                        """)
                        self.stdout.write(self.style.SUCCESS(f'Default value set for {field}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error setting default for {field}: {str(e)}'))
        
        self.stdout.write(self.style.SUCCESS('Database constraints fixed successfully!')) 