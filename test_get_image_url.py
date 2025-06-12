import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'authback.settings')
django.setup()

from spare_parts.models import SparePart
import cloudinary
import cloudinary.uploader

# Get an existing SparePart
try:
    spare_part = SparePart.objects.first()
    print(f"Using SparePart: {spare_part}")
    
    # Get the main image URL
    url = spare_part.get_main_image_url()
    print(f"Main image URL: {url}")
    
    # Check if the URL is valid
    if url:
        import requests
        try:
            response = requests.head(url)
            print(f"URL status: {response.status_code}")
            print(f"URL accessible: {response.status_code == 200}")
        except Exception as e:
            print(f"Error checking URL: {str(e)}")
    else:
        print("No URL returned")
        
except Exception as e:
    print(f"Error: {str(e)}") 