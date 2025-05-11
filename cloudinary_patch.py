import os
import cloudinary
import cloudinary.uploader
import cloudinary.api
from django.conf import settings
from decouple import config
from django.core.files.storage import default_storage
from django.utils.module_loading import import_string

print("Cloudinary patch script running...")

def setup_cloudinary():
    """
    Force Cloudinary setup and correct the storage backend
    """
    # Configure Cloudinary
    cloud_name = config('CLOUDINARY_CLOUD_NAME', default='dz81bjuea')
    api_key = config('CLOUDINARY_API_KEY', default='')
    api_secret = config('CLOUDINARY_API_SECRET', default='')
    
    print(f"Cloudinary credentials loaded:")
    print(f"- Cloud name: {cloud_name}")
    print(f"- API key: {'Set' if api_key else 'Not set'}")
    print(f"- API secret: {'Set' if api_secret else 'Not set'}")
    
    # Force Cloudinary configuration
    cloudinary.config(
        cloud_name=cloud_name,
        api_key=api_key,
        api_secret=api_secret
    )
    
    # Print current storage info for debugging
    print(f"Current default storage: {default_storage.__class__}")
    
    # Directly create storage instance using import_string
    try:
        CloudinaryMediaStorage = import_string('django_cloudinary_storage.storage.MediaCloudinaryStorage')
        
        # Create a test CloudinaryMediaStorage instance
        cloudinary_storage = CloudinaryMediaStorage()
        print(f"Cloudinary storage initialized: {cloudinary_storage.__class__}")
        
        # Generate a test file
        test_file = "test_cloudinary_upload.txt"
        with open(test_file, "w") as f:
            f.write("Test content for Cloudinary upload")
        
        # Test upload directly using Cloudinary API
        result = cloudinary.uploader.upload(
            test_file,
            folder="test",
            resource_type="raw"
        )
        print(f"Direct upload successful! URL: {result['secure_url']}")
        
        # Clean up
        os.remove(test_file)
        return True
    except Exception as e:
        print(f"Cloudinary setup error: {str(e)}")
        return False 

# Execute the function when this script is run directly
if __name__ == "__main__":
    print("Running Cloudinary setup...")
    success = setup_cloudinary()
    print(f"Cloudinary setup {'successful' if success else 'failed'}") 