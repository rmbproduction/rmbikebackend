import sys
import importlib

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

# Try direct Cloudinary upload
print("\nTesting direct Cloudinary upload:")
try:
    import os
    import cloudinary
    import cloudinary.uploader
    from decouple import config
    
    # Get Cloudinary configuration
    cloud_name = config('CLOUDINARY_CLOUD_NAME', default='dz81bjuea')
    api_key = config('CLOUDINARY_API_KEY', default='')
    api_secret = config('CLOUDINARY_API_SECRET', default='')
    
    print(f"Cloud name: {cloud_name}")
    print(f"API key: {'Set' if api_key else 'Not set'}")
    print(f"API secret: {'Set' if api_secret else 'Not set'}")
    
    # Configure Cloudinary
    cloudinary.config(
        cloud_name=cloud_name,
        api_key=api_key,
        api_secret=api_secret
    )
    
    # Create test file - Give it a unique name to avoid pytest trying to run it
    test_file = "cloudinary_test_upload_temp.txt"
    with open(test_file, "w") as f:
        f.write("Test content for Cloudinary upload")
    
    # Test upload
    if api_key and api_secret:
        print("Attempting direct upload to Cloudinary...")
        result = cloudinary.uploader.upload(
            test_file,
            folder="test",
            resource_type="raw"
        )
        print(f"Success! Uploaded to: {result['secure_url']}")
    else:
        print("Skipping upload test as API credentials are not set")
    
    # Clean up
    if os.path.exists(test_file):
        os.remove(test_file)
        
except Exception as e:
    print(f"Error: {str(e)}") 