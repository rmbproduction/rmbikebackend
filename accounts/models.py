from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.crypto import get_random_string
from django.utils import timezone
from cloudinary.models import CloudinaryField


class User(AbstractUser):
    email = models.EmailField(unique=True)
    email_verified = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    # Add related_name for groups and user_permissions to avoid clash with default User model
    groups = models.ManyToManyField(
        'auth.Group', 
        related_name='custom_user_set',  # Custom reverse relation name
        blank=True
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission', 
        related_name='custom_permission_set',  # Custom reverse relation name
        blank=True
    )

    def save(self, *args, **kwargs):
        if self.email:
            if self.email == 'admin@repairmybike.in':
                self.is_staff = True
                self.is_superuser = True
            elif self.email.endswith('@field.repairmybike.in'):
                self.is_staff = False  # Field staff are not regular staff
            elif self.email.endswith('@repairmybike.in'):
                self.is_staff = True
        super().save(*args, **kwargs)

    @property
    def is_admin(self):
        return self.email == 'admin@repairmybike.in'

    @property
    def is_staff_member(self):
        return self.email.endswith('@repairmybike.in') and not self.email.endswith('@field.repairmybike.in')

    @property
    def is_field_staff(self):
        return self.email.endswith('@field.repairmybike.in')

    @property
    def is_customer(self):
        return not (self.is_admin or self.is_staff_member or self.is_field_staff)

class EmailVerificationToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def is_valid(self):
        return self.created_at >= timezone.now() - timezone.timedelta(hours=24)

    @classmethod
    def generate_token(cls, user):
        token = get_random_string(64)
        return cls.objects.create(user=user, token=token)

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    name = models.CharField(max_length=255)
    address = models.TextField(blank=False, default='', help_text="Required field")
    profile_photo = CloudinaryField('image', folder='profiles', null=True, blank=True)
    
    # Location fields
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=10, blank=True, null=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    
    # Vehicle information
    vehicle_name = models.ForeignKey('vehicle.VehicleModel', on_delete=models.SET_NULL, null=True, blank=True)
    vehicle_type = models.ForeignKey('vehicle.VehicleType', on_delete=models.SET_NULL, null=True, blank=True)
    manufacturer = models.ForeignKey('vehicle.Manufacturer', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"

    def save(self, *args, **kwargs):
        # Ensure country is set to India if not specified
        if not self.country:
            self.country = 'India'
        super().save(*args, **kwargs)



class ContactMessage(models.Model):
    """Model for storing contact form submissions"""
    STATUS_CHOICES = (
        ('new', 'New'),
        ('in_progress', 'In Progress'),
        ('responded', 'Responded'),
        ('closed', 'Closed'),
    )

    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    response = models.TextField(blank=True)
    
    # Optional reference to user if they were logged in
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"Contact from {self.name} ({self.email})"
