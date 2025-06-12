import sys
import importlib
import cloudinary
import cloudinary.uploader
import cloudinary.api
from decouple import config

print(f"Python version: {sys.version}")
print(f"Python path: {sys.executable}")

print("\nChecking for specific packages:")
packages_to_check = ['cloudinary', 'django-cloudinary-storage', 'django_cloudinary_storage']

for package in packages_to_check:
    try:
        # Try to import the package
        if package == 'django-cloudinary-storage':
            # Django-cloudinary-storage uses underscores in import
            module_name = 'django_cloudinary_storage'
        else:
            module_name = package
            
        module = importlib.import_module(module_name)
        print(f"✓ {package} is installed (module: {module.__name__})")
    except ImportError:
        print(f"✗ {package} is NOT installed")

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

try:
    # Test Cloudinary connection
    print("\nTesting Cloudinary connection...")
    result = cloudinary.api.ping()
    print(f"Connection successful: {result}")
    
    # Get account info
    print("\nGetting account info...")
    account_info = cloudinary.api.usage()
    print(f"Account info: {account_info}")
    
except Exception as e:
    print(f"Error: {str(e)}") 