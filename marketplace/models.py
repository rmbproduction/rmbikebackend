from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import timedelta
from django.contrib.auth import get_user_model
from cloudinary.models import CloudinaryField

User = get_user_model()

def get_current_year():
    return timezone.now().year

def get_default_valid_until():
    return timezone.now() + timedelta(days=7)

class BaseModel(models.Model):
    """Base model with common timestamp fields"""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ['-created_at']

class Vehicle(BaseModel):
    """
    Vehicle model representing any two-wheeler (bike, scooter, etc.)
    Handles both petrol and electric vehicles
    """
    class VehicleType(models.TextChoices):
        BIKE = 'bike', 'Bike'
        SCOOTER = 'scooter', 'Scooter'
        ELECTRIC_SCOOTER = 'electric_scooter', 'Electric Scooter'
        ELECTRIC_BIKE = 'electric_bike', 'Electric Bike'

    class Status(models.TextChoices):
        AVAILABLE = 'available', 'Available'
        UNDER_INSPECTION = 'under_inspection', 'Under Inspection'
        INSPECTION_DONE = 'inspection_done', 'Inspection Done'
        SOLD = 'sold', 'Sold'

    class FuelType(models.TextChoices):
        PETROL = 'petrol', 'Petrol'
        ELECTRIC = 'electric', 'Electric'

    owner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vehicles',
        help_text="Current owner of the vehicle"
    )
    vehicle_type = models.CharField(
        max_length=20,
        choices=VehicleType.choices,
        default=VehicleType.BIKE,
        help_text="Type of two-wheeler"
    )
    brand = models.CharField(
        max_length=50,
        default='',
        blank=True,
        help_text="Vehicle manufacturer"
    )
    model = models.CharField(
        max_length=50,
        default='',
        blank=True,
        help_text="Vehicle model name"
    )
    Mileage = models.CharField(
        max_length=50,
        default='',
        blank=True,
        help_text="Vehicle Mileage"
    )
    year = models.PositiveIntegerField(
        default=get_current_year,
        validators=[
            MinValueValidator(1900),
            MaxValueValidator(get_current_year)
        ],
        help_text="Manufacturing year"
    )
    registration_number = models.CharField(
        max_length=20,
        unique=True,
        default='',
        blank=True,
        help_text="Vehicle registration number"
    )
    kms_driven = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Total kilometers driven"
    )
    fuel_type = models.CharField(
        max_length=10,
        choices=FuelType.choices,
        default=FuelType.PETROL,
        help_text="Fuel type (petrol/electric)"
    )
    engine_capacity = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Engine capacity in CC (petrol) or Watts (electric)"
    )
    color = models.CharField(
        max_length=30,
        default='Not Specified',
        blank=True,
        help_text="Vehicle color"
    )
    last_service_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of last service"
    )
    insurance_valid_till = models.DateField(
        null=True,
        blank=True,
        help_text="Insurance validity date"
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.UNDER_INSPECTION,
        help_text="Current vehicle status"
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Selling price of the vehicle"
    )
    expected_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Expected price suggested by the seller"
    )
    emi_available = models.BooleanField(
        default=True,
        help_text="Whether EMI is available for this vehicle"
    )
    emi_months = models.JSONField(
        default=list,
        help_text="Available EMI tenures in months"
    )
    images = models.JSONField(
        default=dict,
        help_text='Format: {"thumbnail": "url", "main": "url", "gallery": ["url1", "url2"]}'
    )
    features = models.JSONField(
        default=list,
        help_text="List of vehicle features"
    )
    highlights = models.JSONField(
        default=list,
        help_text="Key highlights of the vehicle"
    )
    bookable = models.BooleanField(
        default=True,
        help_text="Whether the vehicle can be booked",
        null=True,
        blank=True
    )

    class Meta(BaseModel.Meta):
        indexes = [
            models.Index(fields=['vehicle_type', 'brand', 'model']),
            models.Index(fields=['registration_number']),
            models.Index(fields=['status']),
            models.Index(fields=['price']),
        ]

    def __str__(self):
        return f"{self.year} {self.brand or 'Unknown'} {self.model or 'Unknown'} - {self.registration_number}"

    def is_bookable(self):
        """Check if vehicle can be booked"""
        return (
            self.status in [self.Status.AVAILABLE, self.Status.INSPECTION_DONE] 
            and self.bookable
        )

    def calculate_emi(self, months=12, interest_rate=10):
        """Calculate EMI for the vehicle"""
        if not self.emi_available or not self.price:
            return None
        
        principal = float(self.price)
        rate = interest_rate / (12 * 100)  # Monthly interest rate
        
        # EMI calculation formula
        emi = principal * rate * pow(1 + rate, months)
        emi = emi / (pow(1 + rate, months) - 1)
        
        return round(emi, 2)

class SellRequest(BaseModel):
    """
    Represents a request to sell a vehicle
    Tracks the entire selling process from submission to completion
    """
    class Status(models.TextChoices):
        SUBMITTED = 'submitted', 'Submitted'
        CONFIRMED = 'confirmed', 'Confirmed by Call'
        INSPECTION_SCHEDULED = 'inspection_scheduled', 'Inspection Scheduled'
        UNDER_INSPECTION = 'under_inspection', 'Under Inspection'
        SERVICE_CENTER = 'service_center', 'At Service Center'
        INSPECTION_DONE = 'inspection_done', 'Inspection Done'
        OFFER_MADE = 'offer_made', 'Offer Made'
        COUNTER_OFFER = 'counter_offer', 'Counter Offer by Customer'
        DEAL_CLOSED = 'deal_closed', 'Deal Closed'
        REJECTED = 'rejected', 'Rejected'

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sell_requests',
        help_text="User who wants to sell the vehicle"
    )
    vehicle = models.OneToOneField(
        Vehicle,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sell_request',
        help_text="Vehicle being sold"
    )
    
    # Document fields
    registration_certificate = CloudinaryField('document', folder='vehicle_documents/rc', null=True, blank=True,
                                            resource_type='auto', help_text="Vehicle Registration Certificate (PDF/Image)")
    insurance_document = CloudinaryField('document', folder='vehicle_documents/insurance', null=True, blank=True,
                                       resource_type='auto', help_text="Insurance document (PDF/Image)")
    puc_certificate = CloudinaryField('document', folder='vehicle_documents/puc', null=True, blank=True,
                                    resource_type='auto', help_text="Pollution Under Control Certificate (PDF/Image)")
    ownership_transfer = CloudinaryField('document', folder='vehicle_documents/transfer', null=True, blank=True,
                                       resource_type='auto', help_text="Ownership Transfer documents (PDF/Image)")
    additional_documents = CloudinaryField('document', folder='vehicle_documents/additional', null=True, blank=True,
                                         resource_type='auto', help_text="Any additional documents (PDF/Image)")
    
    # Multiple vehicle photos
    photo_front = CloudinaryField('image', folder='vehicle_photos/front', null=True, blank=True,
                                help_text="Front view of vehicle")
    photo_back = CloudinaryField('image', folder='vehicle_photos/back', null=True, blank=True,
                               help_text="Back view of vehicle")
    photo_left = CloudinaryField('image', folder='vehicle_photos/left', null=True, blank=True,
                               help_text="Left side view of vehicle")
    photo_right = CloudinaryField('image', folder='vehicle_photos/right', null=True, blank=True,
                                help_text="Right side view of vehicle")
    photo_dashboard = CloudinaryField('image', folder='vehicle_photos/dashboard', null=True, blank=True,
                                    help_text="Dashboard/Instrument cluster view")
    photo_odometer = CloudinaryField('image', folder='vehicle_photos/odometer', null=True, blank=True,
                                   help_text="Odometer reading")
    photo_engine = CloudinaryField('image', folder='vehicle_photos/engine', null=True, blank=True,
                                 help_text="Engine view")
    photo_extras = CloudinaryField('image', folder='vehicle_photos/extras', null=True, blank=True,
                                 help_text="Additional photos/modifications")
    
    pickup_slot = models.DateTimeField(
        default=timezone.now,
        help_text="Scheduled pickup time"
    )
    pickup_address = models.TextField(
        default='',
        blank=True,
        help_text="Address for vehicle pickup"
    )
    contact_number = models.CharField(
        max_length=15,
        default='',
        blank=True,
        help_text="Contact number for pickup"
    )
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.SUBMITTED,
        help_text="Current status of sell request"
    )
    rejection_reason = models.TextField(
        null=True,
        blank=True,
        help_text="Reason if request is rejected"
    )

    def __str__(self):
        return f"Sell Request - {self.vehicle.registration_number if self.vehicle else 'Unassigned'}"

class InspectionReport(BaseModel):
    """
    Detailed inspection report for a vehicle
    Includes mechanical and cosmetic condition assessment
    """
    class Condition(models.IntegerChoices):
        POOR = 1, 'Poor'
        BELOW_AVERAGE = 2, 'Below Average'
        AVERAGE = 3, 'Average'
        GOOD = 4, 'Good'
        EXCELLENT = 5, 'Excellent'

    sell_request = models.OneToOneField(
        SellRequest,
        on_delete=models.CASCADE,
        related_name='inspection_report',
        help_text="Related sell request"
    )
    inspector = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inspections',
        help_text="Inspector who performed the inspection"
    )

    engine_condition = models.IntegerField(
        choices=Condition.choices,
        default=Condition.POOR,
        help_text="Engine condition rating"
    )
    transmission_condition = models.IntegerField(
        choices=Condition.choices,
        default=Condition.POOR,
        help_text="Transmission condition rating"
    )
    suspension_condition = models.IntegerField(
        choices=Condition.choices,
        default=Condition.POOR,
        help_text="Suspension condition rating"
    )
    tyre_condition = models.IntegerField(
        choices=Condition.choices,
        default=Condition.POOR,
        help_text="Tyre condition rating"
    )
    brake_condition = models.IntegerField(
        choices=Condition.choices,
        default=Condition.POOR,
        help_text="Brake system condition rating"
    )
    electrical_condition = models.IntegerField(
        choices=Condition.choices,
        default=Condition.POOR,
        help_text="Electrical system condition rating"
    )

    frame_condition = models.IntegerField(
        choices=Condition.choices,
        default=Condition.POOR,
        help_text="Frame condition rating"
    )
    paint_condition = models.IntegerField(
        choices=Condition.choices,
        default=Condition.POOR,
        help_text="Paint condition rating"
    )

    overall_rating = models.IntegerField(
        choices=Condition.choices,
        default=Condition.POOR,
        editable=False,
        help_text="Overall vehicle condition rating (auto-calculated)"
    )
    estimated_repair_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Estimated cost of repairs needed"
    )
    remarks = models.TextField(
        default='',
        blank=True,
        help_text="Additional inspection notes"
    )
    inspection_photos = models.JSONField(
        default=list,
        blank=True,
        help_text="List of inspection photo paths"
    )
    passed = models.BooleanField(
        default=False,
        editable=False,
        help_text="Whether vehicle passed inspection (auto-calculated)"
    )

    def save(self, *args, **kwargs):
        """Calculate overall rating and pass/fail status before saving"""
        conditions = [
            self.engine_condition,
            self.transmission_condition,
            self.suspension_condition,
            self.tyre_condition,
            self.brake_condition,
            self.electrical_condition,
            self.frame_condition,
            self.paint_condition
        ]
        # Compute average and determine pass/fail
        self.overall_rating = round(sum(conditions) / len(conditions))
        self.passed = all(c >= self.Condition.BELOW_AVERAGE for c in conditions)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Inspection Report - {self.sell_request.vehicle.registration_number}"

class PurchaseOffer(BaseModel):
    """
    Purchase offer for a vehicle
    Includes pricing details and negotiation status
    """
    class OfferStatus(models.TextChoices):
        INITIAL = 'initial', 'Initial Offer'
        COUNTER_OFFERED = 'counter_offered', 'Counter Offered By Customer'
        ACCEPTED = 'accepted', 'Accepted'
        REJECTED = 'rejected', 'Rejected'
        RENEGOTIATED = 'renegotiated', 'Renegotiated By Company'
        EXPIRED = 'expired', 'Expired'
    
    sell_request = models.OneToOneField(
        SellRequest,
        on_delete=models.CASCADE,
        related_name='offer',
        help_text="Related sell request"
    )

    market_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Estimated market value"
    )
    offer_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Our offer price"
    )
    price_breakdown = models.JSONField(
        default=dict,
        blank=True,
        help_text='Format: {"base_price": 1000, "deductions": {"tyres": -100}}'
    )

    is_negotiable = models.BooleanField(
        default=True,
        help_text="Whether price is negotiable"
    )
    
    status = models.CharField(
        max_length=20,
        choices=OfferStatus.choices,
        default=OfferStatus.INITIAL,
        help_text="Current status of the offer"
    )
    
    counter_offer = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Counter offer from seller"
    )
    
    counter_offer_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When customer made counter offer"
    )
    
    customer_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Customer notes for counter offer"
    )
    
    valid_until = models.DateTimeField(
        default=get_default_valid_until,
        help_text="Offer validity period"
    )

    def save(self, *args, **kwargs):
        """Ensure a default validity period if not specified"""
        if not self.valid_until:
            self.valid_until = get_default_valid_until()
        
        # Update sell request status based on offer status changes
        if self.pk:  # If this is an update
            old_offer = PurchaseOffer.objects.get(pk=self.pk)
            if old_offer.status != self.status:
                if self.status == self.OfferStatus.COUNTER_OFFERED:
                    self.sell_request.status = SellRequest.Status.COUNTER_OFFER
                elif self.status == self.OfferStatus.ACCEPTED:
                    self.sell_request.status = SellRequest.Status.DEAL_CLOSED
                elif self.status == self.OfferStatus.REJECTED:
                    # Don't change sell request status if rejected
                    pass
                self.sell_request.save()
                
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Offer for {self.sell_request.vehicle.registration_number if self.sell_request.vehicle else 'Unassigned Vehicle'}"
        
    def accept_offer(self):
        """Customer accepts the offer"""
        self.status = self.OfferStatus.ACCEPTED
        self.save()
        return True
        
    def reject_offer(self):
        """Customer rejects the offer without counter"""
        self.status = self.OfferStatus.REJECTED  
        self.save()
        return True
        
    def make_counter_offer(self, amount, notes=None):
        """Customer makes a counter offer"""
        self.counter_offer = amount
        self.status = self.OfferStatus.COUNTER_OFFERED
        self.counter_offer_date = timezone.now()
        if notes:
            self.customer_notes = notes
        self.save()
        return True

class VehiclePurchase(models.Model):
    """Model to handle direct vehicle purchases"""
    class Status(models.TextChoices):
        PENDING = 'pending', 'Payment Pending'
        PROCESSING = 'processing', 'Processing'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'
        REFUNDED = 'refunded', 'Refunded'

    vehicle = models.ForeignKey('Vehicle', on_delete=models.PROTECT, related_name='purchases')
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='vehicle_purchases')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    payment_id = models.CharField(max_length=100, blank=True, null=True)
    payment_method = models.CharField(max_length=50, blank=True)
    purchase_date = models.DateTimeField(auto_now_add=True)
    completion_date = models.DateTimeField(null=True, blank=True)
    delivery_address = models.TextField()
    contact_number = models.CharField(max_length=15)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Purchase of {self.vehicle} by {self.buyer}"

    def complete_purchase(self):
        """Complete the purchase and transfer ownership"""
        if self.status == self.Status.PENDING:
            self.status = self.Status.COMPLETED
            self.completion_date = timezone.now()
            self.vehicle.owner = self.buyer
            self.vehicle.status = 'sold'
            self.vehicle.save()
            self.save()
            return True
        return False

class Notification(BaseModel):
    """
    Notification model for marketplace events
    """
    class Type(models.TextChoices):
        NEW_SELL_REQUEST = 'new_sell_request', 'New Sell Request'
        STATUS_CHANGE = 'status_change', 'Status Change'
        OFFER_MADE = 'offer_made', 'Offer Made'
        COUNTER_OFFER = 'counter_offer', 'Counter Offer'
        OFFER_ACCEPTED = 'offer_accepted', 'Offer Accepted'
        OFFER_REJECTED = 'offer_rejected', 'Offer Rejected'
        INSPECTION_SCHEDULED = 'inspection_scheduled', 'Inspection Scheduled'
        INSPECTION_COMPLETED = 'inspection_completed', 'Inspection Completed'
        NEW_BOOKING = 'new_booking', 'New Booking'
        BOOKING_CREATED = 'booking_created', 'Booking Created'
        BOOKING_CONFIRMED = 'booking_confirmed', 'Booking Confirmed'
        BOOKING_COMPLETED = 'booking_completed', 'Booking Completed'
        BOOKING_CANCELLED = 'booking_cancelled', 'Booking Cancelled'
        
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='marketplace_notifications'
    )
    
    type = models.CharField(
        max_length=30,
        choices=Type.choices
    )
    
    sell_request = models.ForeignKey(
        SellRequest,
        on_delete=models.CASCADE,
        related_name='notifications',
        null=True,
        blank=True
    )
    
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    data = models.JSONField(default=dict, blank=True)
    
    def __str__(self):
        return f"{self.type} for {self.user.email}"
    
    class Meta(BaseModel.Meta):
        pass


# Update the PurchaseOffer save method to create notifications
def create_purchase_offer(sender, instance, created, **kwargs):
    """Create notifications when purchase offer is created or updated"""
    from django.db.models.signals import post_save
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    if created:
        # New offer notification for customer
        Notification.objects.create(
            user=instance.sell_request.user,
            type=Notification.Type.OFFER_MADE,
            sell_request=instance.sell_request,
            title="New Offer Received",
            message=f"We have made an offer of ₹{instance.offer_price} for your vehicle.",
            data={
                'offer_id': str(instance.id),
                'offer_price': float(instance.offer_price),
                'valid_until': instance.valid_until.isoformat()
            }
        )
    else:
        # Status change notification
        old_status = PurchaseOffer.objects.get(pk=instance.pk).status
        if old_status != instance.status:
            if instance.status == PurchaseOffer.OfferStatus.COUNTER_OFFERED:
                # Notify admin about counter offer
                admin_users = get_user_model().objects.filter(is_staff=True)
                for admin in admin_users:
                    Notification.objects.create(
                        user=admin,
                        type=Notification.Type.COUNTER_OFFER,
                        sell_request=instance.sell_request,
                        title="Counter Offer Received",
                        message=f"Customer has made a counter offer of ₹{instance.counter_offer}.",
                        data={
                            'offer_id': str(instance.id),
                            'counter_offer': float(instance.counter_offer),
                            'original_offer': float(instance.offer_price)
                        }
                    )


# Update the SellRequest save method to create notifications
def create_sell_request_notification(sender, instance, created, **kwargs):
    """Create notifications when sell request is created or updated"""
    from django.db.models.signals import post_save
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    if created:
        # New sell request notification for admin
        admin_users = get_user_model().objects.filter(is_staff=True)
        for admin in admin_users:
            Notification.objects.create(
                user=admin,
                type=Notification.Type.NEW_SELL_REQUEST,
                sell_request=instance,
                title="New Vehicle Sell Request",
                message=f"New sell request received for {instance.vehicle.registration_number if instance.vehicle else 'a vehicle'}.",
                data={
                    'sell_request_id': instance.id,
                    'user_email': instance.user.email,
                    'contact_number': instance.contact_number
                }
            )
    else:
        # Check if status has changed
        old_status = SellRequest.objects.get(pk=instance.pk).status
        if old_status != instance.status:
            # Status change notification for customer
            Notification.objects.create(
                user=instance.user,
                type=Notification.Type.STATUS_CHANGE,
                sell_request=instance,
                title="Sell Request Status Updated",
                message=f"Your sell request status has been updated to {instance.get_status_display()}.",
                data={
                    'sell_request_id': instance.id,
                    'old_status': old_status,
                    'new_status': instance.status
                }
            )


# Connect signals
from django.db.models.signals import post_save
post_save.connect(create_sell_request_notification, sender=SellRequest)
post_save.connect(create_purchase_offer, sender=PurchaseOffer)

class VehicleBooking(BaseModel):
    """
    Model to handle user bookings of vehicles
    This is used when users want to book a vehicle before purchase
    """
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        CONFIRMED = 'confirmed', 'Confirmed'
        COMPLETED = 'completed', 'Completed' 
        CANCELLED = 'cancelled', 'Cancelled'

    vehicle = models.ForeignKey(
        Vehicle, 
        on_delete=models.PROTECT, 
        related_name='bookings',
        help_text="Vehicle being booked"
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.PROTECT, 
        related_name='vehicle_bookings',
        help_text="User who booked the vehicle"
    )
    status = models.CharField(
        max_length=20, 
        choices=Status.choices, 
        default=Status.PENDING,
        help_text="Current status of the booking"
    )
    booking_date = models.DateTimeField(
        auto_now_add=True,
        help_text="When the booking was created"
    )
    contact_number = models.CharField(
        max_length=15,
        help_text="Contact number for follow-up"
    )
    notes = models.TextField(
        blank=True,
        help_text="Additional notes for the booking"
    )

    def __str__(self):
        return f"Booking for {self.vehicle} by {self.user}"
    
    def confirm_booking(self):
        """Mark booking as confirmed"""
        self.status = self.Status.CONFIRMED
        self.save()
        
        # Create notification for the user
        Notification.objects.create(
            user=self.user,
            type='booking_confirmed',
            title='Booking Confirmed',
            message=f'Your booking for {self.vehicle} has been confirmed.',
            data={'booking_id': self.id, 'vehicle_id': self.vehicle.id}
        )
        
    def complete_booking(self):
        """Mark booking as completed"""
        self.status = self.Status.COMPLETED
        self.save()
        
        # Create notification for the user
        Notification.objects.create(
            user=self.user,
            type='booking_completed',
            title='Booking Completed',
            message=f'Your booking for {self.vehicle} has been completed.',
            data={'booking_id': self.id, 'vehicle_id': self.vehicle.id}
        )
    
    def cancel_booking(self):
        """Cancel the booking"""
        self.status = self.Status.CANCELLED
        self.save()
        
        # Create notification for the user
        Notification.objects.create(
            user=self.user,
            type='booking_cancelled',
            title='Booking Cancelled',
            message=f'Your booking for {self.vehicle} has been cancelled.',
            data={'booking_id': self.id, 'vehicle_id': self.vehicle.id}
        )