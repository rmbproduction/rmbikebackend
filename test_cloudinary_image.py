import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'authback.settings')
django.setup()

import cloudinary
import cloudinary.api
from spare_parts.models import SparePart

# Get the first SparePart with an image
spare_part = SparePart.objects.filter(main_image__isnull=False).first()

if spare_part:
    print(f"Testing image for: {spare_part.name}")
    print(f"Main image value: {spare_part.main_image}")
    print(f"Type: {type(spare_part.main_image)}")
    
    # Test different URL generation methods
    print("\nTesting URL generation methods:")
    
    # Method 1: Using get_main_image_url
    url1 = spare_part.get_main_image_url()
    print(f"1. get_main_image_url(): {url1}")
    
    # Method 2: Using CloudinaryImage
    if isinstance(spare_part.main_image, str):
        try:
            url2 = cloudinary.CloudinaryImage(spare_part.main_image).build_url(secure=True)
            print(f"2. CloudinaryImage().build_url(): {url2}")
        except Exception as e:
            print(f"2. CloudinaryImage().build_url() error: {str(e)}")
    
    # Method 3: Using cloudinary.api.resource
    if isinstance(spare_part.main_image, str):
        try:
            resource = cloudinary.api.resource(spare_part.main_image)
            url3 = resource['secure_url']
            print(f"3. cloudinary.api.resource(): {url3}")
        except Exception as e:
            print(f"3. cloudinary.api.resource() error: {str(e)}")
    
    # Method 4: Direct construction
    if isinstance(spare_part.main_image, str):
        cloud_name = cloudinary.config().cloud_name
        url4 = f"https://res.cloudinary.com/{cloud_name}/image/upload/{spare_part.main_image}"
        print(f"4. Direct URL construction: {url4}")
    
    # Test if the URL is accessible
    import requests
    
    url_to_test = url1 or url4
    if url_to_test:
        try:
            response = requests.head(url_to_test)
            print(f"\nURL accessibility test: {response.status_code}")
            print(f"URL is accessible: {response.status_code == 200}")
        except Exception as e:
            print(f"\nError testing URL: {str(e)}")
else:
    print("No SparePart with an image found") 