from rest_framework import serializers
from .models import (
    Feature, ServiceCategory, Service, ServicePrice, Cart, CartItem,
    FieldStaff, ServiceRequest, ServiceRequestResponse, LiveLocation,
    DistancePricingRule, PricingPlan, AdditionalService, PricingPlanFeature
)
from vehicle.models import VehicleModel
from rest_framework.generics import ListAPIView

class VehicleModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleModel
        fields = '__all__'

class ServicePriceSerializer(serializers.ModelSerializer):
    # Add a field to indicate if this is a custom price or base price
    is_custom_price = serializers.SerializerMethodField()
    
    class Meta:
        model = ServicePrice
        fields = ['id', 'service', 'manufacturer', 'vehicle_model', 'price', 'is_custom_price']
    
    def get_is_custom_price(self, obj):
        # If the object doesn't have an ID, it's a temporary object with base price
        return hasattr(obj, 'id') and obj.id is not None

class FeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feature
        fields = ['id', 'name']

class ServiceSerializer(serializers.ModelSerializer):
    features = FeatureSerializer(many=True, read_only=True)

    class Meta:
        model = Service
        fields = [
            'id', 'name', 'slug', 'description', 'base_price', 'duration', 'warranty',
            'recommended', 'category', 'manufacturers', 'vehicles_models', 'features'
        ]

class ServiceCategorySerializer(serializers.ModelSerializer):
    services = ServiceSerializer(many=True, read_only=True)

    class Meta:
        model = ServiceCategory
        fields = ['uuid', 'name', 'slug', 'image', 'description', 'services']

class CartItemSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source='service.name', read_only=True)
    price = serializers.SerializerMethodField()
    
    def get_price(self, obj):
        return str(obj.service.base_price)
    
    class Meta:
        model = CartItem
        fields = ['id', 'cart', 'service', 'service_name', 'quantity', 'price']

class CartSerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()
    
    def get_items(self, obj):
        cart_items = CartItem.objects.filter(cart=obj)
        return CartItemSerializer(cart_items, many=True).data
    
    class Meta:
        model = Cart
        fields = ['id', 'items']

class FieldStaffSerializer(serializers.ModelSerializer):
    class Meta:
        model = FieldStaff
        fields = '__all__'

class ServiceRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceRequest
        fields = '__all__'

    def get_mechanic_details(self, obj):
        # Assuming you have a method to fetch mechanic details
        return None  # Replace with actual implementation

class ServiceRequestResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceRequestResponse
        fields = '__all__'

class LiveLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LiveLocation
        fields = '__all__'

class PricingPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = PricingPlan
        fields = '__all__'

class AdditionalServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdditionalService
        fields = '__all__'

class PricingPlanFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = PricingPlanFeature
        fields = '__all__'

class FilteredServiceListView(ListAPIView):
    serializer_class = ServiceSerializer

    def get_queryset(self):
        category_id = self.request.query_params.get('category_id')
        if category_id:
            return Service.objects.filter(category__uuid=category_id)
        return Service.objects.all()
