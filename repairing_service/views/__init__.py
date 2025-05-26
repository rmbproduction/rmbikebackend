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
    UserBookingsView,
    GetServiceNowView,
    CancelServiceNowView
)

# Import chatbot views
from .chatbot import chatbot_webhook, analyze_intent, get_chat_history

# Import admin views
from .admin_views import (
    AdminDashboardStatisticsView,
    AdminNotificationsView,
    AdminRequestsView,
    AdminRequestStatusUpdateView
)

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
    'UserBookingsView',
    'GetServiceNowView',
    'CancelServiceNowView',
    # Admin views
    'AdminDashboardStatisticsView',
    'AdminNotificationsView',
    'AdminRequestsView',
    'AdminRequestStatusUpdateView'
] 