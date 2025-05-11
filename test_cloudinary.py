import os
import cloudinary
import cloudinary.uploader
from decouple import config

# Get Cloudinary configuration from environment variables
cloud_name = config('CLOUDINARY_CLOUD_NAME', default='dz81bjuea')
api_key = config('CLOUDINARY_API_KEY', default='')
api_secret = config('CLOUDINARY_API_SECRET', default='')

print(f"Cloudinary configuration:")
print(f"Cloud Name: {cloud_name}")
print(f"API Key: {'*' * len(api_key) if api_key else 'Not set'}")
print(f"API Secret: {'*' * len(api_secret) if api_secret else 'Not set'}")

# Configure cloudinary
cloudinary.config(
    cloud_name=cloud_name,
    api_key=api_key,
    api_secret=api_secret
)

# Create a simple test file
test_file_path = "test_cloudinary_file.txt"
with open(test_file_path, "w") as f:
    f.write("This is a test file for Cloudinary upload")

print(f"Created test file: {test_file_path}")

try:
    # Attempt to upload to Cloudinary
    print("Uploading to Cloudinary...")
    result = cloudinary.uploader.upload(
        test_file_path,
        folder="test",
        resource_type="raw"
    )
    
    print("Upload successful!")
    print(f"File URL: {result['secure_url']}")
    print(f"Resource type: {result['resource_type']}")
    print(f"Public ID: {result['public_id']}")
    
    # If we get here, Cloudinary is correctly configured
    print("\nCLOUDINARY IS CORRECTLY CONFIGURED - DIRECT UPLOADS WORK")
except Exception as e:
    print(f"Error uploading to Cloudinary: {str(e)}")
    print("\nCLOUDINARY CONFIGURATION ERROR - CHECK YOUR CREDENTIALS")
finally:
    # Clean up
    if os.path.exists(test_file_path):
        os.remove(test_file_path)
        print(f"Removed test file: {test_file_path}") 