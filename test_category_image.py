import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'authback.settings')
django.setup()

from spare_parts.models import PartCategory

# Get the first PartCategory with an image
category = PartCategory.objects.filter(image__isnull=False).first()

if category:
    print(f"Testing image for category: {category.name}")
    print(f"Image value: {category.image}")
    print(f"Type: {type(category.image)}")
    
    # Test URL generation
    url = category.get_image_url()
    print(f"Image URL: {url}")
    
    # Test if the URL is accessible
    if url:
        import requests
        try:
            response = requests.head(url)
            print(f"URL status: {response.status_code}")
            print(f"URL is accessible: {response.status_code == 200}")
        except Exception as e:
            print(f"Error checking URL: {str(e)}")
else:
    print("No PartCategory with an image found") 