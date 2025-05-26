from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    VehicleViewSet, SellRequestViewSet, InspectionReportViewSet,
    PurchaseOfferViewSet, VehiclePurchaseViewSet, VehicleBookingViewSet,
    email_vehicle_summary, secure_document_view
)

router = DefaultRouter()
router.register('vehicles', VehicleViewSet, basename='vehicle')
router.register('sell-requests', SellRequestViewSet, basename='sellrequest')
router.register('inspections', InspectionReportViewSet, basename='inspection')
router.register('offers', PurchaseOfferViewSet, basename='offer')
router.register('purchases', VehiclePurchaseViewSet, basename='purchase')
router.register('bookings', VehicleBookingViewSet, basename='booking')

urlpatterns = [
    path('', include(router.urls)),
    path('email-vehicle-summary/', email_vehicle_summary, name='email_vehicle_summary'),
    path('secure-document/<int:sell_request_id>/<str:document_type>/', 
         secure_document_view, 
         name='secure-document'),
]