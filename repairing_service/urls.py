from django.urls import path
from rest_framework.routers import DefaultRouter

# Import views from views directory
from .views.views import (
    PricingPlanListView, 
    create_cart,
    ManufacturerListView,
    VehicleModelListView,
    ServiceCategoryListView,
    ServiceListByCategoryView,
    ServicePriceDetailView,
    CartDetailView,
    RemoveCartItemView,
    AddToCartView,
    CartItemCreateView,
    ServiceRequestViewSet,
    FieldStaffViewSet,
    ServiceRequestResponseDetailView,
    LiveLocationView,
    CalculateDistanceFeeView,
    UpdateCartItemView,
    ClearCartView,
    CreateBookingView,
    CancelBookingView,
    ClearCancelledBookingsView,
    UserBookingsView,
    GetServiceNowView,
    CancelServiceNowView,
    UserCartsView
)

# Import chatbot views
from .views.chatbot import (
    chatbot_webhook, 
    analyze_intent, 
    get_chat_history
)

# Import admin views
from .views.admin_views import (
    AdminDashboardStatisticsView, 
    AdminNotificationsView, 
    AdminRequestsView, 
    AdminRequestStatusUpdateView
)

# Create router for viewsets
router = DefaultRouter()
router.register(r'service-requests', ServiceRequestViewSet, basename='service-request')
router.register(r'field-staff', FieldStaffViewSet, basename='field-staff')

# Define URL patterns
urlpatterns = [
    # Service and Vehicle related endpoints
    path('manufacturers/', ManufacturerListView.as_view(), name='manufacturer-list'),
    path('vehicle-models/', VehicleModelListView.as_view(), name='vehicle-model-list'),
    path('service-categories/', ServiceCategoryListView.as_view(), name='service-category-list'),
    path('services/', ServiceListByCategoryView.as_view(), name='service-list'),
    path('service-price/<uuid:service_id>/', ServicePriceDetailView.as_view(), name='service-price-detail'),
    
    # Cart related endpoints
    path('cart/create/', create_cart, name='create-cart'),
    path('cart/list/', UserCartsView.as_view(), name='user-carts'),
    path('cart/<int:cart_id>/', CartDetailView.as_view(), name='cart-detail'),
    path('cart/<int:cart_id>/add/', AddToCartView.as_view(), name='add-to-cart'),
    path('cart/<int:cart_id>/update-item/', UpdateCartItemView.as_view(), name='update-cart-item'),
    path('cart/<int:cart_id>/clear/', ClearCartView.as_view(), name='clear-cart'),
    path('cart/items/<int:cart_item_id>/', RemoveCartItemView.as_view(), name='remove-cart-item'),
    
    # Service request and booking endpoints
    path('service-requests/<int:service_request_id>/responses/', 
         ServiceRequestResponseDetailView.as_view(), 
         name='service-request-response-detail'),
    path('service-requests/<int:service_request_id>/location/', 
         LiveLocationView.as_view(), 
         name='live-location'),
    
    # Booking management endpoints
    path('bookings/', UserBookingsView.as_view(), name='user-bookings'),
    path('bookings/create/', CreateBookingView.as_view(), name='create-booking'),
    path('bookings/<int:booking_id>/cancel/', CancelBookingView.as_view(), name='cancel-booking'),
    path('bookings/clear-cancelled/', ClearCancelledBookingsView.as_view(), name='clear-cancelled-bookings'),
    
    # Direct service booking endpoints
    path('service-now/', GetServiceNowView.as_view(), name='get-service-now'),
    path('service-now/<int:service_request_id>/cancel/', 
         CancelServiceNowView.as_view(), 
         name='cancel-service-now'),
    
    # Utility endpoints
    path('calculate-distance-fee/', CalculateDistanceFeeView.as_view(), name='calculate-distance-fee'),
    path('pricing-plans/', PricingPlanListView.as_view(), name='pricing-plans'),
    
    # Chatbot endpoints
    path('chatbot/message/', chatbot_webhook, name='chatbot-message'),
    path('chatbot/intent/', analyze_intent, name='chatbot-intent'),
    path('chatbot/history/', get_chat_history, name='chatbot-history'),

    # Admin Dashboard Endpoints
    path('admin/dashboard/statistics/', 
         AdminDashboardStatisticsView.as_view(), 
         name='admin-dashboard-statistics'),
    path('admin/notifications/', 
         AdminNotificationsView.as_view(), 
         name='admin-notifications'),
    path('admin/requests/', 
         AdminRequestsView.as_view(), 
         name='admin-requests'),
    path('admin/requests/<str:request_id>/status/', 
         AdminRequestStatusUpdateView.as_view(), 
         name='admin-request-status-update'),
]

# Add router URLs to urlpatterns
urlpatterns += router.urls
