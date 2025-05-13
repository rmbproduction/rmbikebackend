from django.db import models
from accounts.models import UserProfile
import cloudinary.uploader
from utils.cdn_utils import cdn_manager

# Try to import CloudinaryField, fall back to FileField if unavailable
try:
    from cloudinary.models import CloudinaryField
except ImportError:
    # Create a placeholder CloudinaryField that's actually just a FileField
    # This allows models to load even if Cloudinary isn't installed
    from django.db.models.fields.files import FileField
    class CloudinaryField(FileField):
        def __init__(self, *args, **kwargs):
            # Remove Cloudinary-specific arguments
            folder = kwargs.pop('folder', None)
            super().__init__(*args, **kwargs)

class VehicleType(models.Model):
    name = models.CharField(max_length=50, unique=True)
    image = CloudinaryField('image', folder='vehicle_types', null=True, blank=True)

    def __str__(self):
        return self.name

class Manufacturer(models.Model):
    name = models.CharField(max_length=100, unique=True)
    image = CloudinaryField('image', folder='manufacturers', null=True, blank=True)

    def __str__(self):
        return self.name

class VehicleModel(models.Model):
    name = models.CharField(max_length=100, db_index=True)
    manufacturer = models.ForeignKey(Manufacturer, on_delete=models.CASCADE, db_index=True)
    vehicle_type = models.ForeignKey(VehicleType, on_delete=models.CASCADE, db_index=True)
    
    # Enhanced image fields
    image = CloudinaryField('image', folder='vehicle_models', null=True, blank=True)
    image_front = CloudinaryField('image_front', folder='vehicle_models/front', null=True, blank=True)
    image_back = CloudinaryField('image_back', folder='vehicle_models/back', null=True, blank=True)
    image_side = CloudinaryField('image_side', folder='vehicle_models/side', null=True, blank=True)
    thumbnail = CloudinaryField('thumbnail', folder='vehicle_models/thumbnails', null=True, blank=True)
    
    # Additional metadata
    specs = models.JSONField(default=dict, blank=True, help_text="Technical specifications")
    description = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('name', 'manufacturer')
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['manufacturer', 'vehicle_type']),
        ]

    def __str__(self):
        return f"{self.manufacturer.name} {self.name}"

class VehicleImage(models.Model):
    """Model to store multiple images for user vehicles"""
    POSITION_CHOICES = [
        ('front', 'Front View'),
        ('back', 'Back View'),
        ('left', 'Left Side'),
        ('right', 'Right Side'),
        ('dashboard', 'Dashboard'),
        ('odometer', 'Odometer'),
        ('engine', 'Engine'),
        ('other', 'Other')
    ]
    
    user_vehicle = models.ForeignKey('UserVehicle', related_name='images', on_delete=models.CASCADE, db_index=True)
    image = CloudinaryField('image', folder='user_vehicles/gallery')
    position = models.CharField(max_length=20, choices=POSITION_CHOICES, default='other', db_index=True)
    is_primary = models.BooleanField(default=False, db_index=True)
    caption = models.CharField(max_length=100, blank=True)
    upload_date = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['position', '-is_primary']
        indexes = [
            models.Index(fields=['user_vehicle', 'is_primary']),
            models.Index(fields=['position', 'is_primary']),
        ]
    
    def __str__(self):
        return f"{self.user_vehicle} - {self.get_position_display()}"
    
    def save(self, *args, **kwargs):
        # If this is marked as primary, unmark others
        if self.is_primary:
            VehicleImage.objects.filter(
                user_vehicle=self.user_vehicle, 
                is_primary=True
            ).update(is_primary=False)
        super().save(*args, **kwargs)

    @property
    def image_urls(self):
        """Get all available sizes of the image"""
        if not self.image:
            return None
        
        return {
            size: cdn_manager.get_vehicle_image_url(
                self.user_vehicle.id,
                self.position,
                size
            ) for size in cdn_manager.transformations['vehicle'].keys()
        }

    @property
    def preview_url(self):
        """Get preview size URL of the image"""
        if not self.image:
            return None
        return cdn_manager.get_vehicle_image_url(
            self.user_vehicle.id,
            self.position,
            'preview'
        )

    @property
    def thumbnail_url(self):
        """Get thumbnail size URL of the image"""
        if not self.image:
            return None
        return cdn_manager.get_vehicle_image_url(
            self.user_vehicle.id,
            self.position,
            'thumbnail'
        )

class UserVehicle(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='vehicles', db_index=True)
    
    # Vehicle information stored as strings
    vehicle_type_name = models.CharField(max_length=50, null=True, blank=True, db_index=True)
    manufacturer_name = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    model_name = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    registration_number = models.CharField(max_length=50, unique=True, db_index=True)
    purchase_date = models.DateField(null=True, blank=True)
    
    # Main vehicle image (kept for backward compatibility)
    vehicle_image = CloudinaryField('vehicle_image', folder='user_vehicles', null=True, blank=True)
    
    # Additional fields
    color = models.CharField(max_length=50, blank=True)
    year = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    mileage = models.PositiveIntegerField(null=True, blank=True, help_text="Kilometers driven")
    insurance_expiry = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'registration_number']),
            models.Index(fields=['manufacturer_name', 'model_name']),
            models.Index(fields=['year']),
        ]

    def __str__(self):
        return f"{self.user.email}'s {self.model_name or 'vehicle'}"
    
    @property
    def primary_image(self):
        """Get the primary image or first image if no primary designated"""
        primary = self.images.filter(is_primary=True).first()
        if primary:
            return primary.image
        
        # Fallback to first image
        first_image = self.images.first()
        if first_image:
            return first_image.image
            
        # Final fallback to legacy image
        return self.vehicle_image
