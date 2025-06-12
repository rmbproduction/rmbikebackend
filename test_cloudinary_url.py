import cloudinary
import cloudinary.uploader
import cloudinary.api
from decouple import config

# Get Cloudinary credentials
CLOUDINARY_CLOUD_NAME = config('CLOUDINARY_CLOUD_NAME', default='dz81bjuea')
CLOUDINARY_API_KEY = config('CLOUDINARY_API_KEY', default='')
CLOUDINARY_API_SECRET = config('CLOUDINARY_API_SECRET', default='')

print(f"Cloudinary Config:")
print(f"Cloud Name: {CLOUDINARY_CLOUD_NAME}")
print(f"API Key: {CLOUDINARY_API_KEY}")
print(f"API Secret: {'Set' if CLOUDINARY_API_SECRET else 'Not set'}")

# Configure Cloudinary
cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET,
)

# Test image URL generation
public_id = "spare_parts/4a1adc36-111c-4866-b5ca-20492576834e/air-filter_4a1adc36-111c-4866-b5ca-20492576834e"
print(f"\nTesting URL generation for public_id: {public_id}")

try:
    # Method 1: Using CloudinaryImage
    img1 = cloudinary.CloudinaryImage(public_id)
    url1 = img1.build_url()
    print(f"Method 1 URL: {url1}")
    
    # Method 2: Using cloudinary.utils.cloudinary_url
    url2 = cloudinary.utils.cloudinary_url(public_id)[0]
    print(f"Method 2 URL: {url2}")
    
    # Method 3: Using cloudinary.api.resource
    resource = cloudinary.api.resource(public_id)
    url3 = resource['secure_url']
    print(f"Method 3 URL: {url3}")
    
except Exception as e:
    print(f"Error: {str(e)}") 