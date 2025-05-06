from rest_framework import viewsets, generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.db.models import Q
from .models import VehicleType, Manufacturer, VehicleModel, UserVehicle
from .serializers import (
    VehicleTypeSerializer, ManufacturerSerializer, VehicleModelSerializer, UserVehicleSerializer
)
from .services import VehicleService
from django_filters.rest_framework import DjangoFilterBackend
from .filters import VehicleModelFilter

class VehicleTypeViewSet(viewsets.ModelViewSet):
    queryset = VehicleType.objects.all()
    serializer_class = VehicleTypeSerializer
    permission_classes = [AllowAny]

class ManufacturerViewSet(viewsets.ModelViewSet):
    queryset = Manufacturer.objects.all()
    serializer_class = ManufacturerSerializer
    permission_classes = [AllowAny]

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
