# Make views a proper Python package

# Import views from the views.py file
from .views import (
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
    GetServiceNowView,
    CancelServiceNowView,
    UserBookingsView
)

# Import chatbot views
from .chatbot import chatbot_webhook, analyze_intent, get_chat_history

# Export all views
__all__ = [
    'PricingPlanListView',
    'create_cart',
    'ManufacturerListView',
    'VehicleModelListView',
    'ServiceCategoryListView',
    'ServiceListByCategoryView',
    'ServicePriceDetailView',
    'CartDetailView',
    'RemoveCartItemView',
    'AddToCartView',
    'CartItemCreateView',
    'ServiceRequestViewSet',
    'FieldStaffViewSet',
    'ServiceRequestResponseDetailView',
    'LiveLocationView',
    'CalculateDistanceFeeView',
    'UpdateCartItemView',
    'ClearCartView',
    'chatbot_webhook',
    'analyze_intent',
    'get_chat_history',
    'CreateBookingView',
    'CancelBookingView',
    'ClearCancelledBookingsView',
    'GetServiceNowView',
    'CancelServiceNowView',
    'UserBookingsView'
]