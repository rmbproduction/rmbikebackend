from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    VehicleTypeViewSet, ManufacturerViewSet, VehicleModelViewSet, UserVehicleViewSet
)

router = DefaultRouter()
router.register(r'vehicle-types', VehicleTypeViewSet)
router.register(r'manufacturers', ManufacturerViewSet)
router.register(r'vehicle-models', VehicleModelViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
