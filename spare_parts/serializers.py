from rest_framework import serializers
from .models import PartCategory, SparePart, PartReview
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

    class Meta:
        model = SparePart
        fields = [
            'uuid', 'name', 'slug', 'part_number', 'category', 'category_details',
            'description', 'features', 'specifications',
            'price', 'discounted_price', 'stock_quantity', 'availability_status',
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

class SparePartListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views"""
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = SparePart
        fields = [
            'uuid', 'name', 'slug', 'part_number', 'category_name',
            'price', 'discounted_price', 'availability_status',
            'main_image', 'is_featured'
        ]
        read_only_fields = ['uuid', 'slug'] 