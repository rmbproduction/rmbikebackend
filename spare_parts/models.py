from django.db import models
from cloudinary.models import CloudinaryField
from django.utils.text import slugify
from vehicle.models import Manufacturer, VehicleModel, VehicleType
import uuid
from django.conf import settings
from django.utils import timezone
import math
import cloudinary

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
    main_image = CloudinaryField('image', folder='spare_parts', null=True, blank=True, 
                               transformation={'width': 800, 'height': 600, 'crop': 'fill', 'quality': 'auto'},
                               format='webp')
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
        
    def get_main_image_url(self):
        """Get the URL for the main image with fallback"""
        if self.main_image and hasattr(self.main_image, 'url'):
            return self.main_image.url
        return None
        
    def add_additional_image(self, image_url, public_id=None):
        """Add an image to the additional images list"""
        if not self.additional_images:
            self.additional_images = []
            
        image_data = {
            'url': image_url,
            'created_at': timezone.now().isoformat()
        }
        
        if public_id:
            image_data['public_id'] = public_id
            
        self.additional_images.append(image_data)
        self.save()

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

# New models for cart and order functionality

class PartsCart(models.Model):
    """Shopping cart for spare parts"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('active', 'Active'),
            ('abandoned', 'Abandoned'),
            ('completed', 'Completed')
        ],
        default='active'
    )

    def __str__(self):
        return f"Cart {self.id} - {self.status}"

    @property
    def total_items(self):
        return self.items.count()

    @property
    def total_quantity(self):
        return sum(item.quantity for item in self.items.all())
    
    @property
    def total_price(self):
        return sum(item.get_total_price() for item in self.items.all())

    class Meta:
        ordering = ['-created_at']

class PartsCartItem(models.Model):
    """Individual items in the spare parts shopping cart"""
    class Meta:
        unique_together = ('cart', 'part')

    cart = models.ForeignKey(PartsCart, on_delete=models.CASCADE, related_name='items')
    part = models.ForeignKey(SparePart, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_total_price(self):
        """Calculate total price for this item"""
        return self.quantity * self.part.get_effective_price()

    def __str__(self):
        return f"{self.quantity} x {self.part.name} in Cart {self.cart.id}"

class PartsOrder(models.Model):
    """Order for purchased spare parts"""
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded')
    )

    PAYMENT_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded')
    )

    PURCHASE_TYPE_CHOICES = (
        ('direct', 'Buy Now'),
        ('cart', 'Cart Checkout'),
    )

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True)
    order_number = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    purchase_type = models.CharField(max_length=20, choices=PURCHASE_TYPE_CHOICES, default='cart')
    
    # Customer information
    customer_name = models.CharField(max_length=255, blank=True, null=True)
    customer_email = models.EmailField(blank=True, null=True)
    customer_phone = models.CharField(max_length=20, blank=True, null=True)
    
    # Shipping information
    shipping_address = models.TextField()
    shipping_city = models.CharField(max_length=100)
    shipping_state = models.CharField(max_length=100)
    shipping_pincode = models.CharField(max_length=10)
    
    # Order details
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    final_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Tracking
    tracking_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Distance calculation for delivery charges
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    distance_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        if not self.order_number:
            # Generate a unique order number
            last_order = PartsOrder.objects.order_by('-created_at').first()
            if last_order:
                last_number = int(last_order.order_number[3:])
                self.order_number = f'PRT{str(last_number + 1).zfill(8)}'
            else:
                self.order_number = 'PRT00000001'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order {self.order_number}"

    class Meta:
        ordering = ['-created_at']

class PartsOrderItem(models.Model):
    """Individual items in a parts order"""
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(PartsOrder, related_name='items', on_delete=models.CASCADE)
    part = models.ForeignKey(SparePart, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Price at time of purchase
    total = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        if not self.total:
            self.total = self.quantity * self.price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quantity}x {self.part.name} in order {self.order.order_number}"

class DistancePricingRule(models.Model):
    """Rules for calculating delivery charges based on distance"""
    is_active = models.BooleanField(default=True)
    warehouse_latitude = models.FloatField(default=0.0, help_text="Latitude of the warehouse")
    warehouse_longitude = models.FloatField(default=0.0, help_text="Longitude of the warehouse")
    free_radius_km = models.DecimalField(max_digits=5, decimal_places=2, default=5.00, help_text="Radius in km within which delivery is free")
    base_charge = models.DecimalField(max_digits=10, decimal_places=2, default=50.00, help_text="Base charge for distances beyond free radius")
    per_km_charge = models.DecimalField(max_digits=10, decimal_places=2, default=10.00, help_text="Additional charge per km beyond free radius")
    max_distance_km = models.DecimalField(max_digits=5, decimal_places=2, default=50.00, help_text="Maximum delivery distance in km")

    @classmethod
    def get_active_rule(cls):
        return cls.objects.filter(is_active=True).first()

    def calculate_charges(self, customer_latitude, customer_longitude):
        """Calculate delivery charges based on distance"""
        distance_km = self.calculate_distance(
            self.warehouse_latitude, self.warehouse_longitude,
            customer_latitude, customer_longitude
        )
        
        if distance_km <= float(self.free_radius_km):
            return 0
        
        additional_distance = distance_km - float(self.free_radius_km)
        charge = float(self.base_charge) + (additional_distance * float(self.per_km_charge))
        return charge

    def calculate_distance(self, lat1, lon1, lat2, lon2):
        """Calculate distance between two points in kilometers"""
        R = 6371  # Earth's radius in kilometers

        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

        dlon = lon2 - lon1
        dlat = lat2 - lat1

        a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance = R * c

        return distance

    def __str__(self):
        return f"Distance Pricing Rule (Active: {self.is_active})"

    class Meta:
        verbose_name_plural = "Distance Pricing Rules" 