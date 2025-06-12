import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'authback.settings')
django.setup()

from spare_parts.admin import SparePartAdminForm
from spare_parts.models import SparePart
from vehicle.models import Manufacturer, VehicleModel, VehicleType
import cloudinary
import cloudinary.uploader
from django.core.files.uploadedfile import SimpleUploadedFile

# Create a test image file
test_image_path = "test_image.jpg"
with open(test_image_path, "wb") as f:
    # Create a small JPEG file
    f.write(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xdb\x00C\x01\t\t\t\x0c\x0b\x0c\x18\r\r\x182!\x1c!22222222222222222222222222222222222222222222222222\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x03\x01"\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04\x04\x00\x00\x01}\x01\x02\x03\x00\x04\x11\x05\x12!1A\x06\x13Qa\x07"q\x142\x81\x91\xa1\x08#B\xb1\xc1\x15R\xd1\xf0$3br\x82\t\n\x16\x17\x18\x19\x1a%&\'()*456789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz\x83\x84\x85\x86\x87\x88\x89\x8a\x92\x93\x94\x95\x96\x97\x98\x99\x9a\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xff\xc4\x00\x1f\x01\x00\x03\x01\x01\x01\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xc4\x00\xb5\x11\x00\x02\x01\x02\x04\x04\x03\x04\x07\x05\x04\x04\x00\x01\x02w\x00\x01\x02\x03\x11\x04\x05!1\x06\x12AQ\x07aq\x13"2\x81\x08\x14B\x91\xa1\xb1\xc1\t#3R\xf0\x15br\xd1\n\x16$4\xe1%\xf1\x17\x18\x19\x1a&\'()*56789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz\x82\x83\x84\x85\x86\x87\x88\x89\x8a\x92\x93\x94\x95\x96\x97\x98\x99\x9a\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00?\x00\xfe\xfe(\xa2\x8a\x00\xff\xd9')

# Get an existing SparePart or create a test one
try:
    spare_part = SparePart.objects.first()
    print(f"Using existing SparePart: {spare_part}")
except:
    print("No SparePart found, please create one in the admin first")
    exit(1)

# Get some manufacturers, vehicle models, and vehicle types
manufacturers = list(Manufacturer.objects.all()[:1])
if not manufacturers:
    print("No manufacturers found. Please create at least one manufacturer.")
    exit(1)

vehicle_models = list(VehicleModel.objects.all()[:1])
if not vehicle_models:
    print("No vehicle models found. Please create at least one vehicle model.")
    exit(1)

vehicle_types = list(VehicleType.objects.all()[:1])
if not vehicle_types:
    print("No vehicle types found. Please create at least one vehicle type.")
    exit(1)

print(f"Using manufacturer: {manufacturers[0]}")
print(f"Using vehicle model: {vehicle_models[0]}")
print(f"Using vehicle type: {vehicle_types[0]}")

# Create form data with the test image
uploaded_file = SimpleUploadedFile(
    name='test_image.jpg',
    content=open(test_image_path, 'rb').read(),
    content_type='image/jpeg'
)

# Create form instance
form_data = {
    'name': spare_part.name,
    'slug': spare_part.slug,
    'part_number': spare_part.part_number,
    'category': spare_part.category.pk,
    'description': spare_part.description,
    'price': spare_part.price,
    'stock_quantity': spare_part.stock_quantity,
    'availability_status': spare_part.availability_status,
    'manufacturers': [m.pk for m in manufacturers],
    'vehicle_models': [m.pk for m in vehicle_models],
    'vehicle_types': [t.pk for t in vehicle_types],
    'specifications': '{}',  # Empty JSON
}

file_data = {
    'upload_image': uploaded_file
}

# Create the form
form = SparePartAdminForm(data=form_data, files=file_data, instance=spare_part)

# Check if form is valid
if form.is_valid():
    print("Form is valid")
    try:
        # Save the form
        instance = form.save()
        print(f"Form saved successfully")
        
        # Check if image was set
        if instance.main_image:
            print(f"Image set: {instance.main_image}")
            print(f"Image URL: {instance.main_image.url if hasattr(instance.main_image, 'url') else 'No URL'}")
            
            # Debug CloudinaryField
            print("\nDebugging CloudinaryField:")
            print(f"Type: {type(instance.main_image)}")
            print(f"Dir: {dir(instance.main_image)}")
            
            # Check if the image URL is actually accessible
            import requests
            if hasattr(instance.main_image, 'url'):
                try:
                    response = requests.head(instance.main_image.url)
                    print(f"Image URL accessible: {response.status_code == 200}")
                except Exception as e:
                    print(f"Error checking image URL: {str(e)}")
        else:
            print("Image not set")
    except Exception as e:
        print(f"Error saving form: {str(e)}")
else:
    print("Form is not valid")
    print(f"Form errors: {form.errors}")

# Clean up
if os.path.exists(test_image_path):
    os.remove(test_image_path) 