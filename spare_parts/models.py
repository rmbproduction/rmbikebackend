from django.db import models
from cloudinary.models import CloudinaryField
from django.utils.text import slugify
from vehicle.models import Manufacturer, VehicleModel, VehicleType
import uuid

class PartCategory(models.Model):
    """Categories for spare parts (e.g., Engine Parts, Brake Parts, etc.)"""
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    image = CloudinaryField('image', folder='part_categories', null=True, blank=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcategories')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Part Categories"

class SparePart(models.Model):
    """Individual spare parts that can be purchased"""
    AVAILABILITY_CHOICES = (
        ('in_stock', 'In Stock'),
        ('out_of_stock', 'Out of Stock'),
        ('pre_order', 'Pre-Order'),
        ('discontinued', 'Discontinued')
    )

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    part_number = models.CharField(max_length=50, unique=True)
    category = models.ForeignKey(PartCategory, on_delete=models.CASCADE, related_name='parts')
    description = models.TextField()
    features = models.TextField(blank=True)
    specifications = models.JSONField(default=dict, blank=True)
    
    # Pricing and inventory
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discounted_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stock_quantity = models.PositiveIntegerField(default=0)
    availability_status = models.CharField(max_length=20, choices=AVAILABILITY_CHOICES, default='in_stock')
    
    # Vehicle compatibility
    manufacturers = models.ManyToManyField(Manufacturer, related_name='spare_parts')
    vehicle_models = models.ManyToManyField(VehicleModel, related_name='spare_parts')
    vehicle_types = models.ManyToManyField(VehicleType, related_name='spare_parts')
    
    # Media
    main_image = CloudinaryField('image', folder='spare_parts')
    additional_images = models.JSONField(default=list, blank=True)  # Store URLs of additional images
    
    # SEO and display
    meta_title = models.CharField(max_length=100, blank=True)
    meta_description = models.TextField(blank=True)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        if not self.meta_title:
            self.meta_title = self.name
        super().save(*args, **kwargs)

    def get_effective_price(self):
        """Returns the current effective price (discounted if available)"""
        if self.discounted_price is not None:
            return self.discounted_price
        return self.price

    def is_in_stock(self):
        """Check if the part is currently in stock"""
        return self.stock_quantity > 0 and self.availability_status == 'in_stock'

    def __str__(self):
        return f"{self.name} ({self.part_number})"

    class Meta:
        ordering = ['-created_at']

class PartReview(models.Model):
    """Customer reviews for spare parts"""
    part = models.ForeignKey(SparePart, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField()
    review_text = models.TextField()
    purchase_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('part', 'user')
        ordering = ['-created_at']

    def __str__(self):
        return f"Review by {self.user.username} for {self.part.name}" 