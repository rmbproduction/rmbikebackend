from django.core.management.base import BaseCommand
from marketplace.models import Vehicle

class Command(BaseCommand):
    help = 'Populate vehicle images with default image paths'

    def handle(self, *args, **kwargs):
        vehicles = Vehicle.objects.all()
        total = vehicles.count()
        updated = 0

        self.stdout.write(self.style.SUCCESS(f'Found {total} vehicles. Starting update...'))

        for vehicle in vehicles:
            # Skip vehicles that already have images
            if vehicle.images and (
                vehicle.images.get('front') or 
                vehicle.images.get('main') or 
                vehicle.images.get('thumbnail')):
                continue

            # Set default image paths based on vehicle type
            vehicle_type = vehicle.vehicle_type.lower()
            
            if 'bike' in vehicle_type:
                image_name = 'default-bike.jpg'
            elif 'scooter' in vehicle_type:
                image_name = 'default-scooter.jpg'
            else:
                image_name = 'default-vehicle.jpg'
            
            # Update the images field to include 'front' key
            vehicle.images = {
                'front': image_name,  # Key changed to 'front'
                'main': 'defaults/' + image_name,
                'thumbnail': 'defaults/' + image_name
            }
            
            vehicle.save(update_fields=['images'])
            updated += 1
            
            self.stdout.write(f'Updated vehicle {vehicle.id}: {vehicle.brand} {vehicle.model}')
        
        self.stdout.write(self.style.SUCCESS(f'Successfully updated {updated} of {total} vehicles')) 