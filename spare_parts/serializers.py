from rest_framework import serializers
from .models import PartCategory, SparePart, PartReview, PartsCart, PartsCartItem, PartsOrder, PartsOrderItem, DistancePricingRule
from vehicle.serializers import ManufacturerSerializer, VehicleModelSerializer, VehicleTypeSerializer

class PartCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PartCategory
        fields = ['uuid', 'name', 'slug', 'description', 'image', 'parent', 'is_active']
        read_only_fields = ['uuid', 'slug']

class PartReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = PartReview
        fields = ['uuid', 'user', 'user_name', 'rating', 'review_text', 'purchase_verified', 'created_at']
        read_only_fields = ['uuid', 'user', 'purchase_verified']

    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

class SparePartSerializer(serializers.ModelSerializer):
    category_details = PartCategorySerializer(source='category', read_only=True)
    manufacturers_details = ManufacturerSerializer(source='manufacturers', many=True, read_only=True)
    vehicle_models_details = VehicleModelSerializer(source='vehicle_models', many=True, read_only=True)
    vehicle_types_details = VehicleTypeSerializer(source='vehicle_types', many=True, read_only=True)
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    effective_price = serializers.DecimalField(source='get_effective_price', max_digits=10, decimal_places=2, read_only=True)
    discount_percentage = serializers.SerializerMethodField()
    in_stock = serializers.BooleanField(source='is_in_stock', read_only=True)

    class Meta:
        model = SparePart
        fields = [
            'uuid', 'name', 'slug', 'part_number', 'category', 'category_details',
            'description', 'features', 'specifications',
            'price', 'discounted_price', 'effective_price', 'discount_percentage',
            'stock_quantity', 'availability_status', 'in_stock',
            'manufacturers', 'manufacturers_details',
            'vehicle_models', 'vehicle_models_details',
            'vehicle_types', 'vehicle_types_details',
            'main_image', 'additional_images',
            'meta_title', 'meta_description',
            'is_featured', 'is_active',
            'average_rating', 'review_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['uuid', 'slug', 'average_rating', 'review_count']

    def get_average_rating(self, obj):
        reviews = obj.reviews.all()
        if not reviews:
            return None
        return sum(review.rating for review in reviews) / len(reviews)

    def get_review_count(self, obj):
        return obj.reviews.count()

    def get_discount_percentage(self, obj):
        if obj.discounted_price and obj.price > 0:
            discount = ((obj.price - obj.discounted_price) / obj.price) * 100
            return round(discount, 2)
        return 0

class SparePartListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    effective_price = serializers.DecimalField(source='get_effective_price', max_digits=10, decimal_places=2, read_only=True)
    discount_percentage = serializers.SerializerMethodField()

    class Meta:
        model = SparePart
        fields = [
            'uuid', 'name', 'slug', 'part_number', 'category', 'category_name',
            'price', 'discounted_price', 'effective_price', 'discount_percentage',
            'main_image', 'availability_status', 'is_featured'
        ]
        read_only_fields = ['uuid', 'slug']

    def get_discount_percentage(self, obj):
        if obj.discounted_price and obj.price > 0:
            discount = ((obj.price - obj.discounted_price) / obj.price) * 100
            return round(discount, 2)
        return 0

# New serializers for cart and order

class PartsCartItemSerializer(serializers.ModelSerializer):
    part_details = SparePartListSerializer(source='part', read_only=True)
    total_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True,
        source='get_total_price'
    )

    class Meta:
        model = PartsCartItem
        fields = ['id', 'part', 'part_details', 'quantity', 'total_price']
        read_only_fields = ['id']

    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError("Quantity must be at least 1")
        return value

    def validate(self, data):
        part = data.get('part')
        quantity = data.get('quantity', 1)
        
        if part and not part.is_active:
            raise serializers.ValidationError("This part is not available for purchase")
        
        if part and quantity > part.stock_quantity:
            raise serializers.ValidationError(f"Only {part.stock_quantity} units available in stock")
        
        return data

class PartsCartSerializer(serializers.ModelSerializer):
    items = PartsCartItemSerializer(many=True, read_only=True)
    total_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True,
        source='total_price'
    )
    total_items = serializers.IntegerField(
        read_only=True,
        source='total_items'
    )
    total_quantity = serializers.IntegerField(
        read_only=True,
        source='total_quantity'
    )

    class Meta:
        model = PartsCart
        fields = ['id', 'items', 'total_price', 'total_items', 'total_quantity', 'created_at', 'modified_at', 'status']
        read_only_fields = ['id']

class PartsOrderItemSerializer(serializers.ModelSerializer):
    part_details = SparePartListSerializer(source='part', read_only=True)

    class Meta:
        model = PartsOrderItem
        fields = ['uuid', 'part', 'part_details', 'quantity', 'price', 'total']
        read_only_fields = ['uuid', 'price', 'total']

class PartsOrderSerializer(serializers.ModelSerializer):
    items = PartsOrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = PartsOrder
        fields = [
            'uuid', 'order_number', 'status', 'payment_status', 'purchase_type',
            'customer_name', 'customer_email', 'customer_phone',
            'shipping_address', 'shipping_city', 'shipping_state', 'shipping_pincode',
            'total_amount', 'shipping_charges', 'tax_amount', 'distance_fee',
            'discount_amount', 'final_amount',
            'tracking_number', 'notes', 'items',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'uuid', 'order_number', 'total_amount', 'final_amount',
            'tracking_number'
        ]

class PartsOrderCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating orders from cart or direct purchase"""
    class Meta:
        model = PartsOrder
        fields = [
            'shipping_address', 'shipping_city', 'shipping_state', 'shipping_pincode',
            'customer_name', 'customer_email', 'customer_phone',
            'latitude', 'longitude', 'purchase_type'
        ]

    def validate(self, data):
        # Ensure we have customer information if user is not authenticated
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            if not data.get('customer_name'):
                raise serializers.ValidationError("Customer name is required")
            if not data.get('customer_email'):
                raise serializers.ValidationError("Customer email is required")
            if not data.get('customer_phone'):
                raise serializers.ValidationError("Customer phone is required")
        return data

class DistancePricingRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = DistancePricingRule
        fields = [
            'id', 'is_active', 'warehouse_latitude', 'warehouse_longitude',
            'free_radius_km', 'base_charge', 'per_km_charge', 'max_distance_km'
        ]
        read_only_fields = ['id'] 