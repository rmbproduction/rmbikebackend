from rest_framework import serializers
from django.utils import timezone
from django.core.validators import RegexValidator
from .models import Vehicle, SellRequest, InspectionReport, PurchaseOffer, VehiclePurchase, VehicleBooking
from django.conf import settings
import re

class VehicleSerializer(serializers.ModelSerializer):
    """Serializer for Vehicle model with validation"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    short_description = serializers.SerializerMethodField()
    display_price = serializers.SerializerMethodField()
    front_image_url = serializers.SerializerMethodField()
    back_image_url = serializers.SerializerMethodField()
    left_image_url = serializers.SerializerMethodField()
    right_image_url = serializers.SerializerMethodField()
    dashboard_image_url = serializers.SerializerMethodField()
    features = serializers.SerializerMethodField()
    condition_rating = serializers.SerializerMethodField()
    expected_price = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        required=False,
        allow_null=True
    )
    is_bookable = serializers.SerializerMethodField()
    vehicle_type_display = serializers.CharField(source='get_vehicle_type_display', read_only=True)

    class Meta:
        model = Vehicle
        fields = [
            'id', 'vehicle_type', 'vehicle_type_display', 'brand', 'model', 'year', 'registration_number',
            'kms_driven', 'Mileage', 'fuel_type', 'engine_capacity', 'color',
            'last_service_date', 'insurance_valid_till', 'status', 'status_display',
            'short_description', 'display_price', 'front_image_url', 
            'back_image_url', 'left_image_url', 'right_image_url', 'dashboard_image_url',
            'features', 'condition_rating', 'price', 'expected_price', 'bookable', 'is_bookable'
        ]
        read_only_fields = ['status', 'status_display']

    def get_short_description(self, obj):
        mileage_info = f", Mileage: {obj.Mileage}" if obj.Mileage else ""
        return f"{obj.year} {obj.brand} {obj.model} - {obj.kms_driven:,} km{mileage_info} | {obj.fuel_type}"

    def get_display_price(self, obj):
        # For display purposes, prefer the expected_price over admin's price if available
        # IMPORTANT DISTINCTION:
        # expected_price: The price expected by the seller when submitting their vehicle
        # price: The counter price set by admin for marketplace listing
        price = obj.expected_price if obj.expected_price else obj.price
        
        # Format the price for display
        formatted_price = f"₹{int(price):,}" if price else "₹0"
        
        # Calculate EMI safely
        emi = obj.calculate_emi()
        emi_formatted = f"₹{int(emi):,}/month" if emi is not None else "₹0/month"
        
        return {
            'amount': float(price) if price else 0,
            'currency': 'INR',
            'formatted': formatted_price,
            'emi_available': obj.emi_available,
            'emi_starting_at': emi_formatted
        }

    def get_front_image_url(self, obj):
        # Check if vehicle has a sell request with a front photo
        if hasattr(obj, 'sell_request') and obj.sell_request.photo_front:
            return obj.sell_request.photo_front.url
            
        # Otherwise, check the images dictionary
        front_image = obj.images.get('front') if obj.images else None
        if front_image:
            return settings.MEDIA_URL + 'vehicle_photos/front/' + front_image
            
        # If no specific front image, try other keys
        for key in ['main', 'thumbnail']:
            if obj.images and obj.images.get(key):
                image_path = obj.images.get(key)
                if image_path.startswith('http'):
                    return image_path
                return settings.MEDIA_URL + image_path
                
        # Return default image based on vehicle type
        vehicle_type = obj.vehicle_type.lower()
        if 'bike' in vehicle_type:
            return settings.MEDIA_URL + 'defaults/default-bike.jpg'
        elif 'scooter' in vehicle_type:
            return settings.MEDIA_URL + 'defaults/default-scooter.jpg'
        else:
            return settings.MEDIA_URL + 'defaults/default-vehicle.jpg'

    def get_back_image_url(self, obj):
        if hasattr(obj, 'sell_request') and obj.sell_request.photo_back:
            return obj.sell_request.photo_back.url
        back_image = obj.images.get('back') if obj.images else None
        if back_image:
            return settings.MEDIA_URL + 'vehicle_photos/back/' + back_image
        return None
    
    def get_left_image_url(self, obj):
        if hasattr(obj, 'sell_request') and obj.sell_request.photo_left:
            return obj.sell_request.photo_left.url
        left_image = obj.images.get('left') if obj.images else None
        if left_image:
            return settings.MEDIA_URL + 'vehicle_photos/left/' + left_image
        return None
    
    def get_right_image_url(self, obj):
        if hasattr(obj, 'sell_request') and obj.sell_request.photo_right:
            return obj.sell_request.photo_right.url
        right_image = obj.images.get('right') if obj.images else None
        if right_image:
            return settings.MEDIA_URL + 'vehicle_photos/right/' + right_image
        return None
    
    def get_dashboard_image_url(self, obj):
        if hasattr(obj, 'sell_request') and obj.sell_request.photo_dashboard:
            return obj.sell_request.photo_dashboard.url
        dashboard_image = obj.images.get('dashboard') if obj.images else None
        if dashboard_image:
            return settings.MEDIA_URL + 'vehicle_photos/dashboard/' + dashboard_image
        return None

    def get_features(self, obj):
        features = []
        if obj.engine_capacity:
            features.append(f"{obj.engine_capacity}cc Engine")
        if obj.fuel_type:
            features.append(f"{obj.fuel_type} Powered")
        if obj.Mileage:
            features.append(f"Mileage: {obj.Mileage}")
        if obj.last_service_date:
            features.append("Recently Serviced")
        if obj.insurance_valid_till:
            features.append("Insurance Valid")
        return features

    def get_condition_rating(self, obj):
        # Get condition rating from inspection report if available
        try:
            if hasattr(obj, 'sell_request') and obj.sell_request.inspection_report:
                return {
                    'score': obj.sell_request.inspection_report.overall_rating,
                    'max_score': 5,
                    'label': obj.sell_request.inspection_report.get_overall_rating_display()
                }
        except:
            pass
        return None

    def get_price(self, obj):
        return obj.price

    def get_is_bookable(self, obj):
        return obj.is_bookable()

    def validate_year(self, value):
        if value > timezone.now().year:
            raise serializers.ValidationError("Year cannot be in the future")
        if value < 1900:
            raise serializers.ValidationError("Year cannot be before 1900")
        return value

    def validate_registration_number(self, value):
        if not value:
            raise serializers.ValidationError("Registration number is required")
        # Add your registration number format validation here
        return value.upper()

    def validate(self, data):
        """
        Validate the entire vehicle data to ensure all required fields are present
        """
        errors = {}
        
        # Check required fields
        required_fields = ['vehicle_type', 'brand', 'model', 'year', 'registration_number', 'kms_driven', 'fuel_type']
        for field in required_fields:
            if field not in data or not data[field]:
                errors[field] = f"{field.replace('_', ' ').title()} is required"
        
        # Additional validation for specific fields
        if 'registration_number' in data:
            # Check for duplicate registration number
            if Vehicle.objects.filter(registration_number__iexact=data['registration_number']).exists():
                if self.instance is None or self.instance.registration_number != data['registration_number']:
                    errors['registration_number'] = "This registration number already exists"
        
        # Ensure price has a value greater than 0 for vehicles being sold
        if 'status' in data and data['status'] == 'available' and ('price' not in data or data['price'] <= 0):
            errors['price'] = "Price must be set for vehicles available for sale"
        
        # Validate engine capacity exists for non-electric vehicles
        if 'fuel_type' in data and data['fuel_type'] != 'electric' and ('engine_capacity' not in data or not data['engine_capacity']):
            errors['engine_capacity'] = "Engine capacity is required for non-electric vehicles"
            
        if errors:
            raise serializers.ValidationError(errors)
            
        return data

class InspectionReportSerializer(serializers.ModelSerializer):
    """Serializer for inspection reports with computed fields"""
    inspector_name = serializers.CharField(source='inspector.get_full_name', read_only=True)
    condition_summary = serializers.SerializerMethodField()

    class Meta:
        model = InspectionReport
        fields = [
            'id', 'sell_request', 'inspector', 'inspector_name',
            'engine_condition', 'transmission_condition', 'suspension_condition',
            'tyre_condition', 'brake_condition', 'electrical_condition',
            'frame_condition', 'paint_condition', 'overall_rating',
            'estimated_repair_cost', 'remarks', 'inspection_photos',
            'passed', 'condition_summary', 'created_at'
        ]
        read_only_fields = ['overall_rating', 'passed']

    def get_condition_summary(self, obj):
        return {
            'mechanical': {
                'engine': obj.engine_condition,
                'transmission': obj.transmission_condition,
                'suspension': obj.suspension_condition,
                'brakes': obj.brake_condition,
                'electrical': obj.electrical_condition,
            },
            'cosmetic': {
                'frame': obj.frame_condition,
                'paint': obj.paint_condition,
                'tyres': obj.tyre_condition,
            },
            'overall': obj.overall_rating,
            'verdict': 'Pass' if obj.passed else 'Fail'
        }

class SellRequestSerializer(serializers.ModelSerializer):
    """Serializer for sell requests with nested vehicle details"""
    vehicle_details = VehicleSerializer(source='vehicle', read_only=True)
    inspection_details = InspectionReportSerializer(source='inspection_report', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    documents_complete = serializers.SerializerMethodField()
    documents = serializers.SerializerMethodField()
    photos = serializers.JSONField(required=False)
    
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    contact_number = serializers.CharField(validators=[phone_regex], required=True)

    class Meta:
        model = SellRequest
        fields = [
            'id', 'user', 'vehicle', 'vehicle_details', 'documents',
            'registration_certificate', 'insurance_document', 'puc_certificate',
            'ownership_transfer', 'additional_documents',
            'photos', 'photo_front', 'photo_back', 'photo_left', 'photo_right',
            'photo_dashboard', 'photo_odometer', 'photo_engine', 'photo_extras',
            'pickup_slot', 'pickup_address', 'contact_number',
            'status', 'status_display', 'rejection_reason', 'documents_complete',
            'inspection_details', 'created_at'
        ]
        read_only_fields = ['user', 'status']

    def get_documents(self, obj):
        """Convert individual document fields to a document dictionary"""
        documents = {}
        if obj.registration_certificate:
            documents['rc'] = obj.registration_certificate.url
        if obj.insurance_document:
            documents['insurance'] = obj.insurance_document.url
        if obj.puc_certificate:
            documents['puc'] = obj.puc_certificate.url
        if obj.ownership_transfer:
            documents['transfer'] = obj.ownership_transfer.url
        if obj.additional_documents:
            documents['additional'] = obj.additional_documents.url
        return documents

    def get_documents_complete(self, obj):
        """Check if all required documents are uploaded"""
        required_docs = {'rc', 'insurance', 'puc'}
        documents = self.get_documents(obj)
        submitted_docs = set(documents.keys())
        return {
            'complete': required_docs.issubset(submitted_docs),
            'missing': list(required_docs - submitted_docs)
        }

    def validate_pickup_slot(self, value):
        if value and value < timezone.now():
            raise serializers.ValidationError("Pickup slot cannot be in the past")
        # Ensure pickup slot is during business hours (9 AM to 6 PM)
        if value and (value.hour < 9 or value.hour >= 18):
            raise serializers.ValidationError("Pickup slot must be between 9 AM and 6 PM")
        return value

    def validate_photos(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Photos must be a list")
        required_views = {'front', 'back', 'left', 'right'}
        submitted_views = {photo.get('view', '').lower() for photo in value if isinstance(photo, dict)}
        missing = required_views - submitted_views
        if missing:
            raise serializers.ValidationError(f"Missing required photo views: {', '.join(missing)}")
        return value

    def validate_pickup_address(self, value):
        if not value or len(value.strip()) < 10:
            raise serializers.ValidationError("Please provide a complete pickup address (minimum 10 characters)")
        return value.strip()

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

    def validate_vehicle(self, value):
        """
        Validate that the vehicle exists and hasn't been sold or is part of another sell request
        """
        if value:
            # Check if the vehicle is already part of another active sell request
            existing_requests = SellRequest.objects.filter(
                vehicle=value
            ).exclude(
                status__in=['rejected', 'completed', 'cancelled']
            )
            
            if existing_requests.exists() and self.instance is None:  # Only check on new requests
                raise serializers.ValidationError(
                    "This vehicle is already associated with an active sell request"
                )
        return value

class PurchaseOfferSerializer(serializers.ModelSerializer):
    """Serializer for purchase offers with price validation"""
    sell_request_details = SellRequestSerializer(source='sell_request', read_only=True)
    valid_until_display = serializers.SerializerMethodField()
    price_analysis = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseOffer
        fields = [
            'id', 'sell_request', 'sell_request_details', 'market_value',
            'offer_price', 'price_breakdown', 'is_negotiable', 'accepted',
            'counter_offer', 'valid_until', 'valid_until_display',
            'price_analysis', 'created_at'
        ]
        read_only_fields = ['valid_until']

    def get_valid_until_display(self, obj):
        if not obj.valid_until:
            return None
        return {
            'date': obj.valid_until.date(),
            'time': obj.valid_until.time(),
            'expired': obj.valid_until < timezone.now()
        }

    def get_price_analysis(self, obj):
        if not obj.price_breakdown:
            return None
        
        base_price = obj.price_breakdown.get('base_price', 0)
        deductions = obj.price_breakdown.get('deductions', {})
        total_deductions = sum(deductions.values())
        
        return {
            'base_price': base_price,
            'deductions': deductions,
            'total_deductions': total_deductions,
            'final_price': base_price + total_deductions,
            'market_difference': obj.market_value - obj.offer_price if obj.market_value else None
        }

    def validate(self, data):
        if data.get('offer_price', 0) <= 0:
            raise serializers.ValidationError({"offer_price": "Offer price must be greater than zero"})
        if data.get('counter_offer') is not None and data['counter_offer'] <= 0:
            raise serializers.ValidationError({"counter_offer": "Counter offer must be greater than zero"})
        return data

class VehiclePurchaseSerializer(serializers.ModelSerializer):
    """Serializer for handling vehicle purchases"""
    vehicle_details = VehicleSerializer(source='vehicle', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    contact_number = serializers.CharField(validators=[phone_regex])

    class Meta:
        model = VehiclePurchase
        fields = [
            'id', 'vehicle', 'vehicle_details', 'buyer', 'amount',
            'status', 'status_display', 'payment_method', 'purchase_date',
            'completion_date', 'delivery_address', 'contact_number',
            'notes', 'payment_id'
        ]
        read_only_fields = ['buyer', 'status', 'purchase_date', 'completion_date', 'payment_id']

    def validate_vehicle(self, value):
        if value.status != 'available':
            raise serializers.ValidationError("This vehicle is not available for purchase")
        return value

    def validate_delivery_address(self, value):
        if not value or len(value.strip()) < 10:
            raise serializers.ValidationError("Please provide a complete delivery address (minimum 10 characters)")
        return value.strip()

    def create(self, validated_data):
        validated_data['buyer'] = self.context['request'].user
        validated_data['status'] = VehiclePurchase.Status.PENDING
        return super().create(validated_data)

class VehicleBookingSerializer(serializers.ModelSerializer):
    """Serializer for handling vehicle bookings"""
    vehicle_details = VehicleSerializer(source='vehicle', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be between 10-15 digits with an optional + prefix."
    )
    contact_number = serializers.CharField(validators=[phone_regex])
    user_name = serializers.SerializerMethodField(read_only=True)
    booking_date_display = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = VehicleBooking
        fields = [
            'id', 'vehicle', 'vehicle_details', 'user', 'user_name',
            'status', 'status_display', 'booking_date', 'booking_date_display',
            'contact_number', 'notes'
        ]
        read_only_fields = ['user', 'booking_date']

    def get_user_name(self, obj):
        return obj.user.get_full_name() if obj.user else ""

    def get_booking_date_display(self, obj):
        return obj.booking_date.strftime("%B %d, %Y at %I:%M %p") if obj.booking_date else ""

    def validate_contact_number(self, value):
        """Additional validation for contact number"""
        # Remove any spaces, dashes, or parentheses to get the raw digits
        cleaned_number = re.sub(r'[\s\-\(\)]', '', value)
        
        # Check if it starts with + and if so, ensure it follows international format
        if cleaned_number.startswith('+'):
            if not cleaned_number[1:].isdigit():
                raise serializers.ValidationError("Invalid international phone number format")
        else:
            # If no +, ensure it's all digits
            if not cleaned_number.isdigit():
                raise serializers.ValidationError("Phone number should contain only digits if not in international format")
        
        # Check length after removing the + if present
        digits_only = cleaned_number.replace('+', '')
        if not (10 <= len(digits_only) <= 15):
            raise serializers.ValidationError("Phone number must be between 10-15 digits")
            
        return value

    def validate_vehicle(self, value):
        """Validate that vehicle is available for booking"""
        # Allow booking regardless of status, but log a warning for non-available vehicles
        if value.status != Vehicle.Status.AVAILABLE and value.status != Vehicle.Status.INSPECTION_DONE:
            print(f"Warning: Booking attempted for vehicle {value.id} with status {value.status}")
        return value

    def create(self, validated_data):
        """Create booking with the current user"""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)