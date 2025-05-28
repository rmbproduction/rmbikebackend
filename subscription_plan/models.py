from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import json
from repairing_service.models import ServiceRequest


class Plan(models.Model):
    """
    Represents a subscription plan type (Basic, Premium)
    """
    BASIC = 'basic'
    PREMIUM = 'premium'
    
    PLAN_TYPE_CHOICES = [
        (BASIC, 'Basic'),
        (PREMIUM, 'Premium'),
    ]
    
    name = models.CharField(max_length=100)
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPE_CHOICES, default=BASIC)
    description = models.TextField()
    features_text = models.TextField(blank=True, help_text="Store features as comma-separated values")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.get_plan_type_display()} - {self.name}"
    
    @property
    def features(self):
        """
        Return features as a list from comma-separated text
        """
        if not self.features_text:
            return []
        return [feature.strip() for feature in self.features_text.split(',')]
    
    def set_features(self, features_list):
        """
        Convert a list of features to comma-separated string and save
        """
        if isinstance(features_list, list):
            self.features_text = ', '.join(features_list)
        else:
            self.features_text = str(features_list)


class PlanVariant(models.Model):
    """
    Represents a pricing tier for a plan (quarterly, half-yearly, yearly)
    """
    QUARTERLY = 'quarterly'
    HALF_YEARLY = 'half_yearly'
    YEARLY = 'yearly'
    
    DURATION_CHOICES = [
        (QUARTERLY, 'Quarterly (3 months)'),
        (HALF_YEARLY, 'Half-Yearly (6 months)'),
        (YEARLY, 'Yearly (12 months)'),
    ]
    
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name='variants')
    duration_type = models.CharField(max_length=20, choices=DURATION_CHOICES)
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Original price without discount")
    discounted_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Final price after discount", null=True, blank=True)
    max_visits = models.PositiveIntegerField(help_text="Maximum number of service visits allowed")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.plan.name} - {self.get_duration_type_display()} - ${self.get_effective_price()}"
    
    def get_duration_in_days(self):
        if self.duration_type == self.QUARTERLY:
            return 90
        elif self.duration_type == self.HALF_YEARLY:
            return 180
        elif self.duration_type == self.YEARLY:
            return 365
        return 0
    
    def get_effective_price(self):
        """
        Returns the effective price to charge (discounted if available, otherwise original)
        """
        if self.discounted_price is not None:
            return self.discounted_price
        return self.price


class SubscriptionRequest(models.Model):
    """
    Handles subscription requests pending approval
    """
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (APPROVED, 'Approved'),
        (REJECTED, 'Rejected'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='subscription_requests')
    plan_variant = models.ForeignKey(PlanVariant, on_delete=models.CASCADE)
    request_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    approval_date = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, null=True)
    admin_notes = models.TextField(blank=True, null=True)
    
    # Vehicle information
    vehicle_type = models.ForeignKey('vehicle.VehicleType', on_delete=models.SET_NULL, null=True, blank=True)
    manufacturer = models.ForeignKey('vehicle.Manufacturer', on_delete=models.SET_NULL, null=True, blank=True)
    vehicle_model = models.ForeignKey('vehicle.VehicleModel', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Customer information 
    customer_name = models.CharField(max_length=255, blank=True, null=True)
    customer_email = models.EmailField(blank=True, null=True)
    customer_phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    
    # Schedule information
    schedule_time = models.CharField(max_length=10, blank=True, null=True, help_text="Format: HH:MM")
    
    # Link to ServiceRequest
    service_request = models.OneToOneField(
        ServiceRequest, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='subscription_request'
    )
    
    def __str__(self):
        return f"{self.user.username} - {self.plan_variant.plan.name} ({self.get_status_display()})"
    
    def approve(self, admin_notes=None):
        """
        Approve the subscription request and create an active subscription
        """
        now = timezone.now()
        self.status = self.APPROVED
        self.approval_date = now
        if admin_notes:
            self.admin_notes = admin_notes
        self.save()
        
        # Update the associated service request if it exists
        if self.service_request:
            self.service_request.status = ServiceRequest.STATUS_CONFIRMED
            self.service_request.save()
        
        # Create the actual subscription
        end_date = now + timedelta(days=self.plan_variant.get_duration_in_days())
        UserSubscription.objects.create(
            user=self.user,
            plan_variant=self.plan_variant,
            start_date=now,
            end_date=end_date,
            remaining_visits=self.plan_variant.max_visits
        )
        
        return True
    
    def reject(self, reason):
        """
        Reject the subscription request with a reason
        """
        self.status = self.REJECTED
        self.rejection_reason = reason
        self.save()
        
        # Update the associated service request if it exists
        if self.service_request:
            self.service_request.status = ServiceRequest.STATUS_CANCELLED
            self.service_request.save()
        
        return True


class UserSubscription(models.Model):
    """
    Represents an active user subscription
    """
    ACTIVE = 'active'
    EXPIRED = 'expired'
    CANCELLED = 'cancelled'
    
    STATUS_CHOICES = [
        (ACTIVE, 'Active'),
        (EXPIRED, 'Expired'),
        (CANCELLED, 'Cancelled'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='subscriptions')
    plan_variant = models.ForeignKey(PlanVariant, on_delete=models.CASCADE)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=ACTIVE)
    remaining_visits = models.PositiveIntegerField()
    last_visit_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.plan_variant.plan.name} ({self.get_status_display()})"
    
    def is_active(self):
        return (
            self.status == self.ACTIVE and
            self.end_date > timezone.now() and
            self.remaining_visits > 0
        )
    
    def cancel(self):
        self.status = self.CANCELLED
        self.save()
        return True
    
    def use_visit(self):
        """
        Decrement remaining visits and update last visit date
        """
        if self.is_active() and self.remaining_visits > 0:
            self.remaining_visits -= 1
            self.last_visit_date = timezone.now()
            self.save()
            return True
        return False
    
    def days_remaining(self):
        if not self.is_active():
            return 0
        delta = self.end_date - timezone.now()
        return max(0, delta.days)


class VisitSchedule(models.Model):
    """
    Tracks planned and completed service visits
    """
    SCHEDULED = 'scheduled'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'
    
    STATUS_CHOICES = [
        (SCHEDULED, 'Scheduled'),
        (COMPLETED, 'Completed'),
        (CANCELLED, 'Cancelled'),
    ]
    
    subscription = models.ForeignKey(UserSubscription, on_delete=models.CASCADE, related_name='visits')
    scheduled_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=SCHEDULED)
    service_notes = models.TextField(blank=True, null=True)
    completion_date = models.DateTimeField(null=True, blank=True)
    technician_notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.subscription.user.username} - {self.get_status_display()} - {self.scheduled_date}"
    
    def complete(self, notes=None):
        """
        Mark a visit as completed and update the subscription
        """
        if self.status != self.COMPLETED:
            self.status = self.COMPLETED
            self.completion_date = timezone.now()
            if notes:
                self.technician_notes = notes
            self.save()
            
            # Update the subscription's visit count
            self.subscription.use_visit()
            return True
        return False
    
    def cancel(self, notes=None):
        """
        Cancel a scheduled visit
        """
        if self.status == self.SCHEDULED:
            self.status = self.CANCELLED
            if notes:
                self.service_notes = notes
            self.save()
            return True
        return False
