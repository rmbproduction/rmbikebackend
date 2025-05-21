from django.db import models
from django.db.models.signals import post_migrate
from django.dispatch import receiver
import uuid
from django.db import connection
from cloudinary.models import CloudinaryField
# Removed unused import for django.utils.timezone

class Feature(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class ServiceCategory(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    image = CloudinaryField('image', folder='service_categories', null=True, blank=True)
    description = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.name.lower().replace(' ', '-')
        super(ServiceCategory, self).save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Service Categories"

@receiver(post_migrate)
def create_default_category(sender, **kwargs):
    if sender.name == 'repairing_service':
        # First check if a category with the name already exists using raw SQL
        # to avoid the ORM which might fail if model and DB are out of sync
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM repairing_service_servicecategory WHERE name = 'General Services'")
            count = cursor.fetchone()[0]
            
            if count == 0:
                # Only create if it doesn't exist
                cursor.execute("""
                    INSERT INTO repairing_service_servicecategory (uuid, name, slug, description)
                    VALUES (gen_random_uuid(), 'General Services', 'general-services', 'General bike repair and maintenance services')
                """)

class Service(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.CASCADE,
        related_name='services',
        to_field='uuid',
        db_column='category_uuid'
    )
    description = models.TextField()
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    duration = models.CharField(max_length=50)
    warranty = models.CharField(max_length=100)
    recommended = models.CharField(max_length=100, blank=True, null=True)
    manufacturers = models.ManyToManyField('vehicle.Manufacturer', related_name='services')
    vehicles_models = models.ManyToManyField('vehicle.VehicleModel', related_name='services')
    features = models.ManyToManyField(Feature, related_name='services')
    image = CloudinaryField('image', folder='service_images', null=True, blank=True)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.name.lower().replace(' ', '-')
        super(Service, self).save(*args, **kwargs)

    def discounted_price(self):
        if hasattr(self, 'discount') and self.discount:
            return self.base_price - (self.base_price * self.discount / 100)
        return self.base_price

    def get_price(self, manufacturer=None, vehicle_model=None):
        try:
            if (manufacturer and vehicle_model):
                return ServicePrice.objects.get(service=self, manufacturer=manufacturer, vehicle_model=vehicle_model).price
        except ServicePrice.DoesNotExist:
            return self.base_price

    def __str__(self):
        return self.name

class ServicePrice(models.Model):
    class Meta:
        unique_together = ('service', 'manufacturer', 'vehicle_model')
        
    service = models.ForeignKey(Service, on_delete=models.CASCADE, null=True)
    manufacturer = models.ForeignKey('vehicle.Manufacturer', on_delete=models.CASCADE, null=True, blank=True)
    vehicle_model = models.ForeignKey('vehicle.VehicleModel', on_delete=models.CASCADE, null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.service.name} - {self.price}"

class Cart(models.Model):
    def __str__(self):
        return f"Cart {self.id}"

class CartItem(models.Model):
    class Meta:
        unique_together = ('cart', 'service')

    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.quantity} x {self.service.name} in Cart {self.cart.id}"

class FieldStaff(models.Model):
    def __str__(self):
        return self.user.username

    def update_location(self, latitude, longitude):
        self.latitude = latitude
        self.longitude = longitude
        self.save()

    def is_within_radius(self, customer_latitude, customer_longitude):
        # Radius in kilometers
        radius = 5
        earth_radius = 6371  # Earth radius in kilometers

        lat1_rad = math.radians(self.latitude)
        lon1_rad = math.radians(self.longitude)
        lat2_rad = math.radians(customer_latitude)
        lon2_rad = math.radians(customer_longitude)

        dlon = lon2_rad - lon1_rad
        dlat = lat2_rad - lat1_rad

        a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        distance = earth_radius * c

        return distance <= radius

class ServiceRequest(models.Model):
    # Add status choices
    STATUS_PENDING = 'pending'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'
    
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_CONFIRMED, 'Confirmed'),
        (STATUS_IN_PROGRESS, 'In Progress'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, null=True, blank=True)
    customer_name = models.CharField(max_length=255, null=True, blank=True, default="Customer")
    customer_email = models.EmailField(null=True, blank=True, default="customer@example.com")
    customer_phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    reference = models.CharField(max_length=20, unique=True, default="RMB-DEFAULT")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    scheduled_date = models.DateField(null=True, blank=True)
    schedule_time = models.TimeField(null=True, blank=True)
    services = models.ManyToManyField(Service, related_name='service_requests')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(blank=True, null=True)
    vehicle_type = models.ForeignKey('vehicle.VehicleType', on_delete=models.SET_NULL, null=True, blank=True)
    manufacturer = models.ForeignKey('vehicle.Manufacturer', on_delete=models.SET_NULL, null=True, blank=True)
    vehicle_model = models.ForeignKey('vehicle.VehicleModel', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Location fields for distance calculation
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    distance_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cancelled_requests'
    )
    
    # Add a hidden field to mark cancelled bookings as hidden from UI
    hidden = models.BooleanField(default=False, help_text="If true, this request won't be displayed in the user's UI")

    def cancel_service(self, user):
        """
        Safely cancel a service request
        Returns True if cancellation was successful, False otherwise
        """
        from django.utils import timezone
        
        # Only allow cancellation of pending, confirmed or in_progress bookings
        if self.status in [self.STATUS_PENDING, self.STATUS_CONFIRMED, self.STATUS_IN_PROGRESS]:
            try:
                self.status = self.STATUS_CANCELLED
                self.cancelled_at = timezone.now()
                self.cancelled_by = user
                self.save()
                return True
            except Exception as e:
                print(f"Error cancelling service request: {str(e)}")
                return False
        return False

    def __str__(self):
        return f"Service Request {self.reference or self.id}"

class ServiceRequestResponse(models.Model):
    class Meta:
        unique_together = ('service_request', 'field_staff')

    service_request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE)
    field_staff = models.ForeignKey(FieldStaff, on_delete=models.CASCADE)
    accepted = models.BooleanField(default=False)
    estimated_arrival_time = models.DateTimeField(null=True, blank=True)

class LiveLocation(models.Model):
    class Meta:
        unique_together = ('field_staff', 'service_request')

    field_staff = models.ForeignKey(FieldStaff, on_delete=models.CASCADE)
    service_request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE)
    latitude = models.FloatField()
    longitude = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)

class DistancePricingRule(models.Model):
    def __str__(self):
        return f"Distance Pricing Rule (Active: {self.is_active})"

    class Meta:
        verbose_name_plural = "Distance Pricing Rules"

    is_active = models.BooleanField(default=True)
    service_center_latitude = models.FloatField(default=0.0, help_text="Latitude of the service center")
    service_center_longitude = models.FloatField(default=0.0, help_text="Longitude of the service center")
    free_radius_km = models.DecimalField(max_digits=5, decimal_places=2, default=5.00, help_text="Radius in km within which service is free")
    base_charge = models.DecimalField(max_digits=10, decimal_places=2, default=50.00, help_text="Base charge for distances beyond free radius")
    per_km_charge = models.DecimalField(max_digits=10, decimal_places=2, default=10.00, help_text="Additional charge per km beyond free radius")

    @classmethod
    def get_active_rule(cls):
        try:
            return cls.objects.get(is_active=True)
        except cls.DoesNotExist:
            return None

    def calculate_charges(self, customer_latitude, customer_longitude):
        """Calculate distance-based charges"""
        if not customer_latitude or not customer_longitude:
            return 0
            
        # Calculate distance between service center and customer
        distance_km = self.calculate_distance(
            self.service_center_latitude, 
            self.service_center_longitude,
            float(customer_latitude), 
            float(customer_longitude)
        )
        
        # If within free radius, no charge
        if distance_km <= float(self.free_radius_km):
            return 0
            
        # Otherwise calculate charges
        extra_distance = distance_km - float(self.free_radius_km)
        return float(self.base_charge) + (extra_distance * float(self.per_km_charge))
        
    def calculate_distance(self, lat1, lon1, lat2, lon2):
        """Calculate distance between two points using Haversine formula"""
        import math
        
        # Convert to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        r = 6371  # Radius of earth in kilometers
        
        return c * r

import math
from django.contrib.auth import get_user_model
User = get_user_model()

class PricingPlan(models.Model):
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration = models.CharField(max_length=255)
    description = models.TextField()
    recommended = models.BooleanField(default=False)

    def __str__(self):
        return self.name

class PricingPlanFeature(models.Model):
    pricing_plan = models.ForeignKey(PricingPlan, on_delete=models.CASCADE, related_name='features')
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class AdditionalService(models.Model):
    name = models.CharField(max_length=255)
    price = models.CharField(max_length=255)
    description = models.TextField()

    def __str__(self):
        return self.name
