from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PartCategoryViewSet, 
    SparePartViewSet, 
    create_cart,
    PartsCartDetailView,
    AddToCartView,
    RemoveCartItemView,
    UpdateCartItemView,
    ClearCartView,
    UserCartsView,
    CalculateDistanceFeeView,
    PartsOrderViewSet,
    UserOrdersView,
    check_spare_parts_cloudinary,
    direct_image_upload
)

router = DefaultRouter()
router.register('categories', PartCategoryViewSet)
router.register('parts', SparePartViewSet)
router.register('orders', PartsOrderViewSet, basename='parts-order')

urlpatterns = [
    path('', include(router.urls)),
    
    # Cart management endpoints
    path('cart/create/', create_cart, name='create-parts-cart'),
    path('cart/list/', UserCartsView.as_view(), name='user-parts-carts'),
    path('cart/<int:cart_id>/', PartsCartDetailView.as_view(), name='parts-cart-detail'),
    path('cart/<int:cart_id>/add/', AddToCartView.as_view(), name='add-to-parts-cart'),
    path('cart/<int:cart_id>/update-item/', UpdateCartItemView.as_view(), name='update-parts-cart-item'),
    path('cart/<int:cart_id>/clear/', ClearCartView.as_view(), name='clear-parts-cart'),
    path('cart/items/<int:cart_item_id>/', RemoveCartItemView.as_view(), name='remove-parts-cart-item'),
    
    # Order management endpoints
    path('orders/user/', UserOrdersView.as_view(), name='user-parts-orders'),
    
    # Utility endpoints
    path('calculate-distance-fee/', CalculateDistanceFeeView.as_view(), name='calculate-parts-distance-fee'),
    
    # Diagnostic endpoints
    path('check-cloudinary/', check_spare_parts_cloudinary, name='check-spare-parts-cloudinary'),
    
    # Direct upload endpoint (alternative to admin)
    path('upload-image/', direct_image_upload, name='direct-image-upload'),
] 