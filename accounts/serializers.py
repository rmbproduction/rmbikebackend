# accounts/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from vehicle.models import VehicleModel, VehicleType, Manufacturer
from .models import UserProfile, ContactMessage, EmailVerificationToken
from django.utils import timezone
from datetime import datetime
from django.core.exceptions import ValidationError
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

def get_tokens_for_user(user):
    """Generate JWT tokens for user"""
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

class EmailVerificationTokenSerializer(serializers.ModelSerializer):
    is_expired = serializers.SerializerMethodField()
    hours_remaining = serializers.SerializerMethodField()

    class Meta:
        model = EmailVerificationToken
        fields = ['token', 'created_at', 'is_expired', 'hours_remaining']
        read_only_fields = ['token', 'created_at', 'is_expired', 'hours_remaining']

    def get_is_expired(self, obj):
        now = timezone.now()
        return (now - obj.created_at) > timezone.timedelta(hours=24)

    def get_hours_remaining(self, obj):
        now = timezone.now()
        time_elapsed = now - obj.created_at
        hours_remaining = 24 - (time_elapsed.total_seconds() / 3600)
        return max(0, round(hours_remaining, 1))

class UserSerializer(serializers.ModelSerializer):
    verification_token = EmailVerificationTokenSerializer(read_only=True)
    is_admin = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password', 'verification_token', 'email_verified', 'is_admin')
        extra_kwargs = {
            'password': {'write_only': True},
            'email_verified': {'read_only': True},
            'username': {'required': True, 'min_length': 3},
            'email': {'required': True},
        }

    def validate_password(self, value):
        """Validate password strength"""
        if len(value) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in value):
            raise serializers.ValidationError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in value):
            raise serializers.ValidationError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in value):
            raise serializers.ValidationError("Password must contain at least one number")
        if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in value):
            raise serializers.ValidationError("Password must contain at least one special character")
        return value

    def validate_email(self, value):
        """Validate email format and uniqueness"""
        if get_user_model().objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()  # Convert email to lowercase

    def validate_username(self, value):
        """Validate username format and uniqueness"""
        if get_user_model().objects.filter(username=value).exists():
            raise serializers.ValidationError("This username is already taken.")
        if not value.strip():
            raise serializers.ValidationError("Username cannot be blank.")
        return value.strip()

    def create(self, validated_data):
        user = get_user_model().objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        return user

class UserProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    vehicle_name = serializers.PrimaryKeyRelatedField(queryset=VehicleModel.objects.all(), required=False)
    vehicle_type = serializers.PrimaryKeyRelatedField(queryset=VehicleType.objects.all(), required=False)
    manufacturer = serializers.PrimaryKeyRelatedField(queryset=Manufacturer.objects.all(), required=False)

    class Meta:
        model = UserProfile
        fields = [
            'id', 'user', 'email', 'username', 'name', 'phone',
            'address', 'city', 'state', 'postal_code', 'country',
            'profile_photo', 'vehicle_name', 'vehicle_type', 'manufacturer'
        ]
        read_only_fields = ['id', 'user']

    def create(self, validated_data):
        # Create the UserProfile instance
        profile = UserProfile.objects.create(**validated_data)
        return profile
        
    def update(self, instance, validated_data):
        # Update the instance with the validated fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

    def validate(self, data):
        if self.instance is None:  # Creation
            required_fields = ['name', 'address']
            for field in required_fields:
                if field not in data:
                    raise serializers.ValidationError({
                        field: f"{field.replace('_', ' ').title()} is required"
                    })
        return data

class UserProfileWriteSerializer(serializers.ModelSerializer):
    vehicle_name = serializers.PrimaryKeyRelatedField(
        queryset=VehicleModel.objects.all(),
        required=True,
        error_messages={
            'required': 'Vehicle model is required.',
            'does_not_exist': 'Invalid vehicle model selected.',
            'null': 'Vehicle model cannot be null.'
        }
    )
    vehicle_type = serializers.PrimaryKeyRelatedField(
        queryset=VehicleType.objects.all(),
        required=True,
        error_messages={
            'required': 'Vehicle type is required.',
            'does_not_exist': 'Invalid vehicle type selected.',
            'null': 'Vehicle type cannot be null.'
        }
    )
    manufacturer = serializers.PrimaryKeyRelatedField(
        queryset=Manufacturer.objects.all(),
        required=True,
        error_messages={
            'required': 'Manufacturer is required.',
            'does_not_exist': 'Invalid manufacturer selected.',
            'null': 'Manufacturer cannot be null.'
        }
    )

    class Meta:
        model = UserProfile
        fields = [
            'name', 'phone_number', 'address', 'city',
            'state', 'postal_code', 'country', 'profile_picture', 'bio',
            'vehicle_name', 'vehicle_type', 'manufacturer'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

    def validate(self, data):
        """Ensure all required fields are present and vehicle models match manufacturer"""
        # Required field validation
        required_fields = ['address', 'city', 'state', 'postal_code', 'phone_number', 
                         'vehicle_name', 'vehicle_type', 'manufacturer']
        
        for field in required_fields:
            if field not in data:
                raise serializers.ValidationError({field: f"{field.replace('_', ' ').title()} is required"})
            if data[field] is None:
                raise serializers.ValidationError({field: f"{field.replace('_', ' ').title()} cannot be null"})
        
        # Check vehicle model belongs to selected manufacturer
        if 'vehicle_name' in data and 'manufacturer' in data:
            vehicle_model = data['vehicle_name']
            manufacturer = data['manufacturer']
            
            if vehicle_model.manufacturer.id != manufacturer.id:
                raise serializers.ValidationError({
                    'vehicle_name': f"Selected vehicle model doesn't belong to {manufacturer.name}"
                })
        
        # Check vehicle model type matches selected type
        if 'vehicle_name' in data and 'vehicle_type' in data:
            vehicle_model = data['vehicle_name']
            vehicle_type = data['vehicle_type']
            
            if vehicle_model.vehicle_type.id != vehicle_type.id:
                raise serializers.ValidationError({
                    'vehicle_type': f"Selected vehicle type doesn't match the vehicle model's type"
                })
        
        return data

class ContactMessageSerializer(serializers.ModelSerializer):
    """Serializer for contact messages"""
    class Meta:
        model = ContactMessage
        fields = ['id', 'name', 'email', 'phone', 'message', 'created_at']
        read_only_fields = ['id', 'created_at']
        
    def validate_email(self, value):
        """Validate email"""
        if not value:
            raise serializers.ValidationError("Email is required")
        return value
        
    def validate_name(self, value):
        """Validate name"""
        if not value:
            raise serializers.ValidationError("Name is required")
        return value
        
    def validate_message(self, value):
        """Validate message"""
        if not value:
            raise serializers.ValidationError("Message is required")
        if len(value) < 10:
            raise serializers.ValidationError("Message must be at least 10 characters")
        return value

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        # Add custom claims with proper UTC timestamps
        now = timezone.now()
        utc_timestamp = int(now.timestamp())
        
        token['username'] = user.username
        token['email'] = user.email
        token['is_active'] = user.is_active
        token['email_verified'] = user.email_verified
        token['date_joined'] = user.date_joined.isoformat()
        token['iat'] = utc_timestamp
        token['token_type'] = 'refresh'
        
        # Log token generation with UTC timestamps
        logger.info(f"Generated token pair for user {user.email}", extra={
            'exp': datetime.fromtimestamp(token['exp']).isoformat(),
            'iat': datetime.fromtimestamp(utc_timestamp).isoformat(),
            'user_id': user.id,
            'utc_now': now.isoformat()
        })
        
        return token

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    remember_me = serializers.BooleanField(required=False, default=False)

class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()
    
    def validate_refresh(self, value):
        if not value.strip():
            raise serializers.ValidationError("Refresh token cannot be empty")
        return value

class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()

class PasswordResetConfirmSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise ValidationError("Passwords do not match")
        return data