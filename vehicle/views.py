from rest_framework import viewsets, generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import action, api_view
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.http import JsonResponse
from django.core.files.storage import default_storage
from django.conf import settings
from .models import VehicleType, Manufacturer, VehicleModel, UserVehicle
from .serializers import (
    VehicleTypeSerializer, ManufacturerSerializer, VehicleModelSerializer, UserVehicleSerializer
)
from .services import VehicleService
from django_filters.rest_framework import DjangoFilterBackend
from .filters import VehicleModelFilter
from tools.cache_utils import cache_api_response, CACHE_TIMES
from utils.cdn_utils import cdn_manager

class VehicleTypeViewSet(viewsets.ModelViewSet):
    queryset = VehicleType.objects.all()
    serializer_class = VehicleTypeSerializer
    permission_classes = [AllowAny]
    
    @cache_api_response(timeout=CACHE_TIMES['STATIC'], key_prefix="vehicle_types")
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @cache_api_response(timeout=CACHE_TIMES['STATIC'], key_prefix="vehicle_type")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

class ManufacturerViewSet(viewsets.ModelViewSet):
    queryset = Manufacturer.objects.all()
    serializer_class = ManufacturerSerializer
    permission_classes = [AllowAny]
    
    @cache_api_response(timeout=CACHE_TIMES['STATIC'], key_prefix="manufacturers")
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @cache_api_response(timeout=CACHE_TIMES['STATIC'], key_prefix="manufacturer")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

class VehicleModelViewSet(viewsets.ModelViewSet):
    queryset = VehicleModel.objects.all()
    serializer_class = VehicleModelSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_class = VehicleModelFilter

    def get_queryset(self):
        queryset = super().get_queryset()
        manufacturer_id = self.request.query_params.get('manufacturer')
        vehicle_type_id = self.request.query_params.get('vehicle_type')
        
        if manufacturer_id:
            queryset = queryset.filter(manufacturer_id=manufacturer_id)
        if vehicle_type_id:
            queryset = queryset.filter(vehicle_type_id=vehicle_type_id)
            
        return queryset.select_related('manufacturer', 'vehicle_type')
    
    @cache_api_response(timeout=CACHE_TIMES['LOOKUP'], key_prefix="vehicle_models")
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @cache_api_response(timeout=CACHE_TIMES['LOOKUP'], key_prefix="vehicle_model")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

class UserVehicleViewSet(viewsets.ModelViewSet):
    queryset = UserVehicle.objects.all()
    serializer_class = UserVehicleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user.profile)

    def perform_create(self, serializer):
        vehicle_data = serializer.validated_data
        marketplace_vehicle, user_vehicle = VehicleService.create_user_vehicle(
            self.request.user,
            vehicle_data
        )
        return user_vehicle

    def perform_update(self, serializer):
        vehicle_data = serializer.validated_data
        marketplace_vehicle, user_vehicle = VehicleService.update_user_vehicle(
            serializer.instance,
            vehicle_data
        )
        return user_vehicle

    @action(detail=True, methods=['get'])
    @cache_api_response(timeout=CACHE_TIMES['USER'], key_prefix="vehicle_details")
    def full_details(self, request, pk=None):
        """Get combined details from both vehicle models"""
        user_vehicle = self.get_object()
        details = VehicleService.get_vehicle_details(user_vehicle.registration_number)
        if not details:
            return Response(
                {"detail": "Vehicle details not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        return Response(details)

    @action(detail=True, methods=['GET'])
    def image_urls(self, request, pk=None):
        """Get all image URLs for a vehicle"""
        vehicle = self.get_object()
        
        # Get all images for the vehicle
        images = vehicle.images.all()
        
        # Get URLs for each image
        urls = {}
        for image in images:
            urls[image.position] = {
                'urls': image.image_urls,
                'preview': image.preview_url,
                'thumbnail': image.thumbnail_url,
                'is_primary': image.is_primary,
                'caption': image.caption
            }
        
        return Response({
            'status': 'success',
            'data': urls
        })

    @action(detail=True, methods=['GET'])
    def upload_params(self, request, pk=None):
        """Get upload parameters for vehicle images"""
        vehicle = self.get_object()
        
        params = cdn_manager.get_upload_params(
            'vehicle',
            vehicle.id,
            {
                'allowed_formats': ['jpg', 'png', 'webp'],
                'max_file_size': 5 * 1024 * 1024  # 5MB
            }
        )
        
        return Response({
            'status': 'success',
            'data': params
        })

@api_view(['GET'])
def check_cloudinary(request):
    """Test view to check Cloudinary configuration"""
    import cloudinary
    
    # Get the Cloudinary configuration directly from cloudinary package
    config = cloudinary.config()
    storage_class = str(default_storage.__class__)
    
    return JsonResponse({
        'storage_class': storage_class,
        'is_cloudinary': 'cloudinary' in storage_class.lower(),
        'cloud_name': config.cloud_name,
        'credentials_configured': bool(config.cloud_name and config.api_key and config.api_secret),
        'default_storage': settings.DEFAULT_FILE_STORAGE,
    })
