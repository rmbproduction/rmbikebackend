from django.core.management.base import BaseCommand
from marketplace.models import Vehicle

class Command(BaseCommand):
    help = 'Populate vehicle images with default image paths'

    def handle(self, *args, **kwargs):
        vehicles = Vehicle.objects.all()
        total = vehicles.count()
        updated = 0

        self.stdout.write(self.style.SUCCESS(f'Found {total} vehicles. Starting update...'))
        
        # Use Cloudinary hosted default images
        default_images = {
            'bike': 'https://res.cloudinary.com/dz81bjuea/image/upload/v1747051234/defaults/default-bike_mdwkyt.jpg',
            'scooter': 'https://res.cloudinary.com/dz81bjuea/image/upload/v1747051234/defaults/default-scooter_a5ghnr.jpg',
            'default': 'https://res.cloudinary.com/dz81bjuea/image/upload/v1747051234/defaults/default-vehicle_x9w3po.jpg'
        }

        for vehicle in vehicles:
            # Skip vehicles that already have images with URLs
            if vehicle.images and (
                vehicle.images.get('front', '').startswith('http') or 
                vehicle.images.get('main', '').startswith('http') or 
                vehicle.images.get('thumbnail', '').startswith('http')):
                continue

            # Set default image paths based on vehicle type
            vehicle_type = vehicle.vehicle_type.lower()
            
            if 'bike' in vehicle_type:
                image_url = default_images['bike']
            elif 'scooter' in vehicle_type:
                image_url = default_images['scooter']
            else:
                image_url = default_images['default']
            
            # Update the images field with Cloudinary URLs
            vehicle.images = {
                'front': image_url,
                'main': image_url,
                'thumbnail': image_url
            }
            
            vehicle.save(update_fields=['images'])
            updated += 1
            
            self.stdout.write(f'Updated vehicle {vehicle.id}: {vehicle.brand} {vehicle.model}')
        
        self.stdout.write(self.style.SUCCESS(f'Successfully updated {updated} of {total} vehicles')) 