from rest_framework import serializers
from .models import VehicleType, Manufacturer, VehicleModel, UserVehicle, VehicleImage
from accounts.models import UserProfile

class VehicleTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleType
        fields = ('id', 'name', 'image')  # You can also add more fields if required

class ManufacturerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Manufacturer
        fields = ('id', 'name', 'image')

class VehicleModelSerializer(serializers.ModelSerializer):
    manufacturer_name = serializers.CharField(source='manufacturer.name', read_only=True)
    vehicle_type_name = serializers.CharField(source='vehicle_type.name', read_only=True)

    class Meta:
        model = VehicleModel
        fields = ('id', 'name', 'manufacturer', 'manufacturer_name', 'vehicle_type', 'vehicle_type_name', 'image')

class UserVehicleSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=UserProfile.objects.all())
    vehicle_type_name = serializers.CharField(max_length=50)
    manufacturer_name = serializers.CharField(max_length=100)
    model_name = serializers.CharField(max_length=100)

    class Meta:
        model = UserVehicle
        fields = ('id', 'user', 'vehicle_type_name', 'manufacturer_name', 'model_name', 'registration_number', 'purchase_date', 'vehicle_image', 'color', 'year', 'mileage', 'insurance_expiry', 'notes')

class VehicleImageSerializer(serializers.ModelSerializer):
    image_urls = serializers.SerializerMethodField()
    preview_url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = VehicleImage
        fields = [
            'id', 'user_vehicle', 'image', 'position', 'is_primary',
            'caption', 'upload_date', 'image_urls', 'preview_url', 'thumbnail_url'
        ]

    def get_image_urls(self, obj):
        return obj.image_urls

    def get_preview_url(self, obj):
        return obj.preview_url

    def get_thumbnail_url(self, obj):
        return obj.thumbnail_url
