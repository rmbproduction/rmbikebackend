from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    VehicleTypeViewSet, ManufacturerViewSet, VehicleModelViewSet, UserVehicleViewSet, check_cloudinary
)

router = DefaultRouter()
router.register(r'vehicle-types', VehicleTypeViewSet)
router.register(r'manufacturers', ManufacturerViewSet)
router.register(r'vehicle-models', VehicleModelViewSet)
router.register(r'user-vehicles', UserVehicleViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('check-cloudinary/', check_cloudinary, name='check-cloudinary'),
]
