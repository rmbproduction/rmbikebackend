from rest_framework import serializers
from .models import Plan, PlanVariant, SubscriptionRequest, UserSubscription, VisitSchedule
from repairing_service.models import ServiceRequest
import time


class PlanSerializer(serializers.ModelSerializer):
    features = serializers.ListField(read_only=False, required=False)
    
    class Meta:
        model = Plan
        fields = ['id', 'name', 'plan_type', 'description', 'features', 'features_text', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']
        extra_kwargs = {
            'features_text': {'write_only': True}
        }
    
    def to_representation(self, instance):
        # Get the default representation
        ret = super().to_representation(instance)
        # Remove the write-only field from response
        if 'features_text' in ret:
            del ret['features_text']
        return ret
    
    def create(self, validated_data):
        features_list = validated_data.pop('features', None)
        plan = Plan.objects.create(**validated_data)
        
        if features_list:
            plan.set_features(features_list)
            plan.save()
        
        return plan
    
    def update(self, instance, validated_data):
        features_list = validated_data.pop('features', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        if features_list is not None:
            instance.set_features(features_list)
        
        instance.save()
        return instance


class PlanVariantSerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(source='plan.name', read_only=True)
    plan_type = serializers.CharField(source='plan.plan_type', read_only=True)
    duration_display = serializers.CharField(source='get_duration_type_display', read_only=True)
    
    class Meta:
        model = PlanVariant
        fields = [
            'id', 'plan', 'plan_name', 'plan_type', 'duration_type', 
            'duration_display', 'price', 'discounted_price', 'max_visits', 'is_active'
        ]


class SubscriptionRequestSerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(source='plan_variant.plan.name', read_only=True)
    duration_type = serializers.CharField(source='plan_variant.get_duration_type_display', read_only=True)
    price = serializers.DecimalField(
        source='plan_variant.price',
        max_digits=10,
        decimal_places=2,
        read_only=True
    )
    discounted_price = serializers.DecimalField(
        source='plan_variant.discounted_price',
        max_digits=10,
        decimal_places=2,
        read_only=True,
        allow_null=True
    )
    username = serializers.CharField(source='user.username', read_only=True)
    service_request_id = serializers.IntegerField(source='service_request.id', read_only=True, allow_null=True)
    service_reference = serializers.CharField(source='service_request.reference', read_only=True, allow_null=True)
    service_status = serializers.CharField(source='service_request.status', read_only=True, allow_null=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = SubscriptionRequest
        fields = [
            'id', 'user', 'username', 'plan_variant', 'plan_name', 
            'duration_type', 'price', 'discounted_price', 'request_date', 'status', 'status_display',
            'approval_date', 'rejection_reason', 'admin_notes',
            # Vehicle information fields
            'vehicle_type', 'manufacturer', 'vehicle_model',
            # Customer information fields
            'customer_name', 'customer_email', 'customer_phone',
            'address', 'city', 'state', 'postal_code',
            # Service request relation
            'service_request', 'service_request_id', 'service_reference', 'service_status'
        ]
        read_only_fields = ['user', 'approval_date', 'rejection_reason', 'admin_notes', 'status', 'service_request']
    
    def create(self, validated_data):
        # Check if user already has an active subscription
        user = validated_data.get('user')
        active_subscriptions = UserSubscription.objects.filter(
            user=user,
            status=UserSubscription.ACTIVE
        )
        
        if active_subscriptions.exists():
            raise serializers.ValidationError(
                "You already have an active subscription. Please cancel it before requesting a new one."
            )
        
        # Check if user already has a pending request
        pending_requests = SubscriptionRequest.objects.filter(
            user=user,
            status=SubscriptionRequest.PENDING
        )
        
        if pending_requests.exists():
            raise serializers.ValidationError(
                "You already have a pending subscription request."
            )
        
        # Generate a unique reference number using timestamp
        timestamp = int(time.time())
        reference = f"SUB-{user.id}-{validated_data.get('plan_variant').id}-{timestamp}"
        
        # Check if reference already exists (just to be extra safe)
        while ServiceRequest.objects.filter(reference=reference).exists():
            timestamp = int(time.time())
            reference = f"SUB-{user.id}-{validated_data.get('plan_variant').id}-{timestamp}"
        
        try:
            # Create a ServiceRequest for this subscription
            service_request = ServiceRequest.objects.create(
                user=user,
                customer_name=validated_data.get('customer_name'),
                customer_email=validated_data.get('customer_email'),
                customer_phone=validated_data.get('customer_phone'),
                address=validated_data.get('address'),
                city=validated_data.get('city'),
                state=validated_data.get('state'),
                postal_code=validated_data.get('postal_code'),
                reference=reference,
                status=ServiceRequest.STATUS_PENDING,
                notes="Subscription request",
                vehicle_type_id=validated_data.get('vehicle_type').id if validated_data.get('vehicle_type') else None,
                manufacturer_id=validated_data.get('manufacturer').id if validated_data.get('manufacturer') else None,
                vehicle_model_id=validated_data.get('vehicle_model').id if validated_data.get('vehicle_model') else None
            )
            
            # Create the subscription request and link to the service request
            subscription_request = SubscriptionRequest.objects.create(
                user=user,
                plan_variant=validated_data.get('plan_variant'),
                vehicle_type=validated_data.get('vehicle_type'),
                manufacturer=validated_data.get('manufacturer'),
                vehicle_model=validated_data.get('vehicle_model'),
                customer_name=validated_data.get('customer_name'),
                customer_email=validated_data.get('customer_email'),
                customer_phone=validated_data.get('customer_phone'),
                address=validated_data.get('address'),
                city=validated_data.get('city'),
                state=validated_data.get('state'),
                postal_code=validated_data.get('postal_code'),
                service_request=service_request
            )
                
            return subscription_request
            
        except Exception as e:
            # If anything fails during creation, make sure to clean up
            if 'service_request' in locals():
                service_request.delete()
            raise serializers.ValidationError(f"Failed to create subscription request: {str(e)}")


class UserSubscriptionSerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(source='plan_variant.plan.name', read_only=True)
    plan_type = serializers.CharField(source='plan_variant.plan.plan_type', read_only=True)
    duration_type = serializers.CharField(source='plan_variant.get_duration_type_display', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    is_currently_active = serializers.BooleanField(source='is_active', read_only=True)
    remaining_days = serializers.IntegerField(source='days_remaining', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    max_visits = serializers.IntegerField(source='plan_variant.max_visits', read_only=True)
    
    class Meta:
        model = UserSubscription
        fields = [
            'id', 'user', 'username', 'plan_variant', 'plan_name', 
            'plan_type', 'duration_type', 'start_date', 'end_date', 
            'status', 'status_display', 'remaining_visits', 'max_visits', 'last_visit_date', 
            'is_currently_active', 'remaining_days', 'created_at'
        ]
        read_only_fields = ['start_date', 'end_date', 'status', 'remaining_visits']


class VisitScheduleSerializer(serializers.ModelSerializer):
    subscription_id = serializers.IntegerField(source='subscription.id', read_only=True)
    username = serializers.CharField(source='subscription.user.username', read_only=True)
    plan_name = serializers.CharField(source='subscription.plan_variant.plan.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = VisitSchedule
        fields = [
            'id', 'subscription', 'subscription_id', 'username', 
            'plan_name', 'scheduled_date', 'status', 'status_display',
            'service_notes', 'completion_date', 'technician_notes',
            'created_at'
        ]
        read_only_fields = ['completion_date', 'technician_notes']
    
    def validate(self, data):
        # Validate that the subscription is active and has remaining visits
        subscription = data.get('subscription')
        if not subscription.is_active():
            raise serializers.ValidationError(
                "This subscription is not active or has no remaining visits."
            )
        
        # Check if scheduled date is in the future
        scheduled_date = data.get('scheduled_date')
        if scheduled_date and scheduled_date < serializers.DateTimeField().to_representation(
            serializers.timezone.now()
        ):
            raise serializers.ValidationError(
                "Scheduled date must be in the future."
            )
            
        return data


class VisitCompletionSerializer(serializers.Serializer):
    """
    Serializer for completing a visit
    """
    technician_notes = serializers.CharField(required=False, allow_blank=True)


class VisitCancellationSerializer(serializers.Serializer):
    """
    Serializer for cancelling a visit
    """
    cancellation_notes = serializers.CharField(required=False, allow_blank=True) 