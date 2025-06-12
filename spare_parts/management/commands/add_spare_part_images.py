from django.core.management.base import BaseCommand
from spare_parts.models import SparePart
from django.conf import settings
import requests
import tempfile
import os
import cloudinary.uploader
import random

class Command(BaseCommand):
    help = 'Add placeholder images to spare parts that don\'t have images'

    def handle(self, *args, **options):
        # Image search terms for each category
        category_image_searches = {
            'engine_parts': ['motorcycle engine part', 'bike engine component'],
            'body_parts': ['motorcycle body part', 'bike fairing'],
            'lighting': ['motorcycle headlight', 'bike indicator light'],
            'electrical': ['motorcycle battery', 'bike electrical part'],
            'brakes': ['motorcycle brake shoe', 'bike brake part'],
            'suspension': ['motorcycle suspension', 'bike shock absorber'],
            'accessories': ['motorcycle accessory', 'bike mirror stand']
        }
        
        # Get all spare parts without images
        parts = SparePart.objects.all()
        self.stdout.write(f"Found {parts.count()} spare parts in total")
        
        # Process each part
        for part in parts:
            try:
                # Skip parts that already have main images
                if part.main_image and part.main_image.url:
                    self.stdout.write(self.style.WARNING(f"Skipping {part.name} - already has an image"))
                    continue
                
                # Get appropriate search term based on category
                category_slug = part.category.slug
                search_terms = category_image_searches.get(category_slug, ['motorcycle part'])
                search_term = f"{part.name} {random.choice(search_terms)}"
                
                # Use a placeholder image URL (replace with a real image API in production)
                # For demo purposes, we'll use placeholder.com
                width = random.randint(400, 800)
                height = random.randint(300, 600)
                image_url = f"https://via.placeholder.com/{width}x{height}.png?text={part.name.replace(' ', '+')}"
                
                self.stdout.write(f"Fetching image for {part.name} using search term: {search_term}")
                
                # In a real scenario, you'd use an image API like Unsplash, Pexels, etc.
                # For this example, we'll use placeholder images
                
                # Download the image
                response = requests.get(image_url)
                if response.status_code != 200:
                    self.stdout.write(self.style.ERROR(f"Failed to download image for {part.name}"))
                    continue
                
                # Save the image to a temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
                    temp_file.write(response.content)
                    temp_file_path = temp_file.name
                
                # Upload to Cloudinary
                self.stdout.write(f"Uploading image for {part.name} to Cloudinary")
                try:
                    upload_result = cloudinary.uploader.upload(
                        temp_file_path,
                        folder="spare_parts",
                        public_id=f"{part.slug}_{random.randint(1000, 9999)}",
                    )
                    
                    # Update the part with the image URL
                    part.main_image = upload_result['public_id']
                    part.save()
                    
                    self.stdout.write(self.style.SUCCESS(f"Added image for {part.name}"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Failed to upload image for {part.name}: {str(e)}"))
                
                # Clean up the temporary file
                os.unlink(temp_file_path)
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error processing {part.name}: {str(e)}"))
        
        self.stdout.write(self.style.SUCCESS("Completed adding images to spare parts")) 