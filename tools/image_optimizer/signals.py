from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.conf import settings
import logging
from .utils import optimize_image, create_webp_version, create_responsive_images

logger = logging.getLogger(__name__)

# Set this to True to enable automatic image optimization
ENABLE_AUTO_OPTIMIZATION = getattr(settings, 'ENABLE_AUTO_OPTIMIZATION', False)

# Models and fields to automatically optimize
IMAGE_FIELDS_CONFIG = {
    'vehicle.VehicleImage': ['image'],
    'marketplace.Vehicle': ['photo_front', 'photo_back', 'photo_left', 'photo_right', 
                           'photo_dashboard', 'photo_odometer', 'photo_engine', 'photo_extras'],
    'vehicle.UserVehicle': ['vehicle_image'],
    'repairing_service.Service': ['image']
}

@receiver(pre_save)
def optimize_images_on_save(sender, instance, **kwargs):
    """
    Signal handler to optimize images before saving them
    """
    if not ENABLE_AUTO_OPTIMIZATION:
        return
    
    # Check if we should process images for this model
    sender_key = f"{sender._meta.app_label}.{sender._meta.object_name}"
    
    if sender_key not in IMAGE_FIELDS_CONFIG:
        return
    
    try:
        # Get the fields to optimize for this model
        fields_to_optimize = IMAGE_FIELDS_CONFIG[sender_key]
        
        for field_name in fields_to_optimize:
            image_field = getattr(instance, field_name, None)
            
            # Check if the field has a file and it's a new upload
            if image_field and hasattr(image_field, 'file') and hasattr(image_field, '_committed') and not image_field._committed:
                logger.debug(f"Optimizing {field_name} for {sender_key} instance {instance.pk}")
                
                # Optimize the image
                optimized_image = optimize_image(image_field)
                
                # Replace original with optimized version if successful
                if optimized_image:
                    setattr(instance, field_name, optimized_image)
    except Exception as e:
        # Log errors but don't prevent saving
        logger.error(f"Error optimizing images for {sender}: {str(e)}")

@receiver(post_save)
def create_responsive_versions(sender, instance, created, **kwargs):
    """
    Signal handler to create responsive image versions after saving
    Only creates responsive versions for newly created instances to avoid
    redundant processing
    """
    # Skip if auto optimization is disabled or for updates
    if not ENABLE_AUTO_OPTIMIZATION or not created:
        return
    
    # Check if we should process images for this model
    sender_key = f"{sender._meta.app_label}.{sender._meta.object_name}"
    
    # Only handle VehicleImage for responsive versions to avoid overprocessing
    if sender_key != 'vehicle.VehicleImage':
        return
    
    try:
        # Create responsive versions for vehicle images
        image_field = getattr(instance, 'image', None)
        if image_field and hasattr(image_field, 'file'):
            logger.debug(f"Creating responsive versions for {sender_key} instance {instance.pk}")
            
            # Create WebP version only for vehicle images
            webp_version = create_webp_version(image_field)
            
            # We can store this in instance attributes or save to a related model
            # For now, just logging the creation
            if webp_version:
                logger.info(f"Created WebP version for {sender_key} instance {instance.pk}")
                
            # Create other responsive versions as needed
            # This would typically be saved to a related model or storage
            responsive_versions = create_responsive_images(image_field)
            if responsive_versions:
                logger.info(f"Created {len(responsive_versions)} responsive versions for {sender_key} instance {instance.pk}")
    except Exception as e:
        # Log errors
        logger.error(f"Error creating responsive versions for {sender}: {str(e)}") 