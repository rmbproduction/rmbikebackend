from django.db import models
from accounts.models import UserProfile

class VehicleType(models.Model):
    name = models.CharField(max_length=50, unique=True)
    image = models.ImageField(upload_to='vehicle_types/', null=True, blank=True)

    def __str__(self):
        return self.name

class Manufacturer(models.Model):
    name = models.CharField(max_length=100, unique=True)
    image = models.ImageField(upload_to='manufacturer_images/', null=True, blank=True)

    def __str__(self):
        return self.name

class VehicleModel(models.Model):
    name = models.CharField(max_length=100)
    manufacturer = models.ForeignKey(Manufacturer, on_delete=models.CASCADE)
    vehicle_type = models.ForeignKey(VehicleType, on_delete=models.CASCADE)
    
    # Enhanced image fields
    image = models.ImageField(upload_to='vehicle_models/', null=True, blank=True)
    image_front = models.ImageField(upload_to='vehicle_models/front/', null=True, blank=True)
    image_back = models.ImageField(upload_to='vehicle_models/back/', null=True, blank=True)
    image_side = models.ImageField(upload_to='vehicle_models/side/', null=True, blank=True)
    thumbnail = models.ImageField(upload_to='vehicle_models/thumbnails/', null=True, blank=True)
    
    # Additional metadata
    specs = models.JSONField(default=dict, blank=True, help_text="Technical specifications")
    description = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('name', 'manufacturer')

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
    
    user_vehicle = models.ForeignKey('UserVehicle', related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='user_vehicles/gallery/')
    position = models.CharField(max_length=20, choices=POSITION_CHOICES, default='other')
    is_primary = models.BooleanField(default=False)
    caption = models.CharField(max_length=100, blank=True)
    upload_date = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['position', '-is_primary']
    
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

class UserVehicle(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='vehicles')
    
    # Vehicle information stored as strings
    vehicle_type_name = models.CharField(max_length=50, null=True, blank=True)
    manufacturer_name = models.CharField(max_length=100, null=True, blank=True)
    model_name = models.CharField(max_length=100, null=True, blank=True)
    registration_number = models.CharField(max_length=50, unique=True)
    purchase_date = models.DateField(null=True, blank=True)
    
    # Main vehicle image (kept for backward compatibility)
    vehicle_image = models.ImageField(upload_to='user_vehicles/', null=True, blank=True)
    
    # Additional fields
    color = models.CharField(max_length=50, blank=True)
    year = models.PositiveIntegerField(null=True, blank=True)
    mileage = models.PositiveIntegerField(null=True, blank=True, help_text="Kilometers driven")
    insurance_expiry = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

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
