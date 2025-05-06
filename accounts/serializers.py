# accounts/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from vehicle.models import VehicleModel, VehicleType, Manufacturer
from .models import UserProfile, ContactMessage, EmailVerificationToken

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    is_admin = serializers.BooleanField(read_only=True)
    is_staff_member = serializers.BooleanField(read_only=True)
    is_field_staff = serializers.BooleanField(read_only=True)
    is_customer = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = (
            'username', 
            'email', 
            'password',
            'email_verified',
            'is_active',
            'date_joined',
            'is_admin',
            'is_staff_member',
            'is_field_staff',
            'is_customer'
        )
        extra_kwargs = {
            'password': {'write_only': True},
            'email': {'required': True},
            'username': {'required': True},
            'email_verified': {'read_only': True},
            'date_joined': {'read_only': True},
            'is_active': {'read_only': True}
        }

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        return user

class EmailVerificationTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailVerificationToken
        fields = ['token', 'created_at']
        read_only_fields = ['token', 'created_at']

class UserProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    vehicle_name = serializers.PrimaryKeyRelatedField(
        queryset=VehicleModel.objects.all(),
        required=False,
        allow_null=True
    )
    vehicle_type = serializers.PrimaryKeyRelatedField(
        queryset=VehicleType.objects.all(),
        required=False,
        allow_null=True
    )
    manufacturer = serializers.PrimaryKeyRelatedField(
        queryset=Manufacturer.objects.all(),
        required=False,
        allow_null=True
    )

    class Meta:
        model = UserProfile
        fields = [
            'email', 'username', 'name', 'address', 'profile_photo',
            'vehicle_name', 'vehicle_type', 'manufacturer',
            'preferredLocation', 'latitude', 'longitude',
            'city', 'state', 'country', 'postal_code', 'phone'
        ]
        read_only_fields = ['email', 'username']

    def create(self, validated_data):
        # Remove vehicle-related fields as they don't exist in the UserProfile model
        vehicle_name = validated_data.pop('vehicle_name', None)
        vehicle_type = validated_data.pop('vehicle_type', None)
        manufacturer = validated_data.pop('manufacturer', None)
        
        # Create the UserProfile instance
        profile = UserProfile.objects.create(**validated_data)
        
        # Here you could handle the vehicle fields if needed
        # For example, create a UserVehicle instance with these values
        # But that would need additional logic beyond this fix
        
        return profile
        
    def update(self, instance, validated_data):
        # Remove vehicle-related fields as they don't exist in the UserProfile model
        validated_data.pop('vehicle_name', None)
        validated_data.pop('vehicle_type', None)
        validated_data.pop('manufacturer', None)
        
        # Update the instance with the remaining fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        return instance

    def validate(self, data):
        if self.instance is None:  # Creation
            required_fields = ['name', 'address', 'preferredLocation']
            for field in required_fields:
                if field not in data:
                    raise serializers.ValidationError({
                        field: f"{field.replace('_', ' ').title()} is required"
                    })

        # Vehicle validation only if vehicle-related fields are provided
        vehicle_fields = {'vehicle_name', 'vehicle_type', 'manufacturer'}
        provided_vehicle_fields = set(data.keys()) & vehicle_fields

        if provided_vehicle_fields:
            if len(provided_vehicle_fields) != len(vehicle_fields):
                missing = vehicle_fields - provided_vehicle_fields
                raise serializers.ValidationError({
                    "vehicle": f"If providing vehicle information, all fields are required: {', '.join(missing)}"
                })

            vehicle_model = data.get('vehicle_name')
            manufacturer = data.get('manufacturer')
            vehicle_type = data.get('vehicle_type')

            if vehicle_model and manufacturer:
                if vehicle_model.manufacturer.id != manufacturer.id:
                    raise serializers.ValidationError({
                        'vehicle_name': f"Selected vehicle model doesn't belong to {manufacturer.name}"
                    })

            if vehicle_model and vehicle_type:
                if vehicle_model.vehicle_type.id != vehicle_type.id:
                    raise serializers.ValidationError({
                        'vehicle_type': f"Selected vehicle type doesn't match the vehicle model's type"
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
            'email', 'name', 'username', 'address', 'profile_photo', 
            'vehicle_name', 'vehicle_type', 'manufacturer', 
            'preferredLocation', 'latitude', 'longitude',
            'city', 'state', 'country', 'postal_code', 'phone'
        ]
        read_only_fields = ['email']

    def validate(self, data):
        """Ensure all required fields are present and vehicle models match manufacturer"""
        # Required field validation
        required_fields = ['address', 'city', 'state', 'postal_code', 'phone', 
                         'vehicle_name', 'vehicle_type', 'manufacturer', 'preferredLocation']
        
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
        fields = [
            'id', 
            'name', 
            'email', 
            'phone', 
            'message', 
            'created_at',
            'updated_at',
            'status',
            'response',
            'user'
        ]
        read_only_fields = [
            'id', 
            'created_at', 
            'updated_at',
            'status',
            'response'
        ]
        
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

        # Add custom claims
        token['username'] = user.username
        token['email'] = user.email
        token['is_active'] = user.is_active
        token['email_verified'] = user.email_verified
        token['date_joined'] = str(user.date_joined)
        
        return token

def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)

    # Add custom claims
    refresh['username'] = user.username
    refresh['email'] = user.email
    refresh['is_active'] = user.is_active
    refresh['email_verified'] = user.email_verified
    refresh['date_joined'] = str(user.date_joined)

    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(style={'input_type': 'password'})

class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(
        required=True,
        help_text="Enter your refresh token to logout",
        error_messages={
            'required': 'Refresh token is required to log out',
            'blank': 'Refresh token cannot be blank',
        },
        style={
            'base_template': 'textarea.html',
            'placeholder': 'Paste your refresh token here',
            'rows': 3,
            'cols': 40
        }
    )
    
    def validate_refresh(self, value):
        if not value.strip():
            raise serializers.ValidationError("Refresh token cannot be empty")
        return value

class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField(
        required=True,
        help_text="Enter your registered email address",
        error_messages={
            'required': 'Email is required',
            'invalid': 'Please enter a valid email address'
        }
    )

    def validate_email(self, value):
        try:
            User.objects.get(email=value)
            return value
        except User.DoesNotExist:
            # We don't want to reveal if the email exists or not
            return value

class PasswordResetConfirmSerializer(serializers.Serializer):
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        help_text="Enter your new password (minimum 8 characters)"
    )