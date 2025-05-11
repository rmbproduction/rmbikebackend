from io import BytesIO
import os
from PIL import Image, ImageOps
from django.core.files.base import ContentFile
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# Supported image formats
SUPPORTED_FORMATS = {
    'JPEG': 'JPEG',
    'PNG': 'PNG',
    'WEBP': 'WEBP'
}

# Default quality settings
DEFAULT_QUALITY = 85
DEFAULT_WEBP_QUALITY = 80

# Size presets (width in pixels)
SIZE_PRESETS = {
    'thumbnail': 150,
    'small': 320,
    'medium': 640,
    'large': 1024,
    'xl': 1920
}

def create_webp_version(image_field, quality=DEFAULT_WEBP_QUALITY):
    """Convert any image to WebP format with optimized settings"""
    if not image_field:
        return None
    
    try:
        # Get original image
        img = Image.open(image_field)
        
        # Convert to RGB if needed (WebP doesn't support CMYK or other modes)
        if img.mode not in ('RGB', 'RGBA'):
            img = img.convert('RGB')
        
        # Create output buffer
        output = BytesIO()
        
        # Save as WebP
        img.save(output, format='WEBP', quality=quality, optimize=True)
        output.seek(0)
        
        # Get original filename and create WebP version
        original_name = os.path.splitext(os.path.basename(image_field.name))[0]
        webp_name = f"{original_name}.webp"
        
        # Return content file
        return ContentFile(output.read(), name=webp_name)
    except Exception as e:
        logger.error(f"Error creating WebP version: {str(e)}")
        return None

def create_responsive_images(image_field, sizes=None, formats=None):
    """
    Create responsive image versions in multiple sizes and formats
    Returns a dictionary of {size_format: ContentFile} pairs
    """
    if not image_field:
        return {}
    
    sizes = sizes or ['thumbnail', 'medium', 'large']
    formats = formats or ['JPEG', 'WEBP']
    responsive_images = {}
    
    try:
        # Get original image
        img = Image.open(image_field)
        
        # Convert to RGB if needed
        if img.mode not in ('RGB', 'RGBA'):
            img = img.convert('RGB')
        
        # Get original filename without extension
        original_name = os.path.splitext(os.path.basename(image_field.name))[0]
        
        for size in sizes:
            # Get target width
            target_width = SIZE_PRESETS.get(size, SIZE_PRESETS['medium'])
            
            # Calculate height maintaining aspect ratio
            width_percent = (target_width / float(img.size[0]))
            target_height = int((float(img.size[1]) * float(width_percent)))
            
            # Resize image
            resized_img = ImageOps.contain(img, (target_width, target_height))
            
            for fmt in formats:
                if fmt not in SUPPORTED_FORMATS:
                    continue
                
                output = BytesIO()
                format_name = SUPPORTED_FORMATS[fmt]
                
                # Set quality based on format
                quality = DEFAULT_WEBP_QUALITY if format_name == 'WEBP' else DEFAULT_QUALITY
                
                # Save with format-specific options
                if format_name == 'JPEG':
                    resized_img.save(output, format=format_name, quality=quality, optimize=True, progressive=True)
                elif format_name == 'PNG':
                    resized_img.save(output, format=format_name, optimize=True, compress_level=9)
                else:
                    resized_img.save(output, format=format_name, quality=quality)
                
                output.seek(0)
                
                # Create filename
                ext = format_name.lower()
                filename = f"{original_name}_{size}.{ext}"
                
                # Store in result dictionary
                responsive_images[f"{size}_{ext}"] = ContentFile(output.read(), name=filename)
        
        return responsive_images
    except Exception as e:
        logger.error(f"Error creating responsive images: {str(e)}")
        return {}

def optimize_image(image_field, max_size=1920, quality=DEFAULT_QUALITY, format='JPEG'):
    """Basic image optimization: resize if too large and optimize quality"""
    if not image_field:
        return None
    
    try:
        # Get original image
        img = Image.open(image_field)
        
        # Convert to RGB if needed
        if img.mode not in ('RGB', 'RGBA'):
            img = img.convert('RGB')
        
        # Resize if larger than max_size
        if img.width > max_size or img.height > max_size:
            # Maintain aspect ratio
            if img.width > img.height:
                height = int((max_size / img.width) * img.height)
                img = ImageOps.contain(img, (max_size, height))
            else:
                width = int((max_size / img.height) * img.width)
                img = ImageOps.contain(img, (width, max_size))
        
        # Create output buffer
        output = BytesIO()
        
        # Save with optimized settings
        format_name = SUPPORTED_FORMATS.get(format, 'JPEG')
        if format_name == 'JPEG':
            img.save(output, format=format_name, quality=quality, optimize=True, progressive=True)
        elif format_name == 'PNG':
            img.save(output, format=format_name, optimize=True, compress_level=9)
        else:  # WEBP or others
            img.save(output, format=format_name, quality=quality)
        
        output.seek(0)
        
        # Get original filename and extension
        original_name = os.path.splitext(os.path.basename(image_field.name))[0]
        ext = format_name.lower()
        optimized_name = f"{original_name}_optimized.{ext}"
        
        return ContentFile(output.read(), name=optimized_name)
    except Exception as e:
        logger.error(f"Error optimizing image: {str(e)}")
        return None 