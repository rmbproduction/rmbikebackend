from rest_framework import viewsets, permissions, status, filters, generics
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
import cloudinary.uploader
from utils.cdn_utils import cdn_manager
from .models import (
    PartCategory, SparePart, PartReview, 
    PartsCart, PartsCartItem, PartsOrder, PartsOrderItem, DistancePricingRule
)
from .serializers import (
    PartCategorySerializer,
    SparePartSerializer,
    SparePartListSerializer,
    PartReviewSerializer,
    PartsCartSerializer,
    PartsCartItemSerializer,
    PartsOrderSerializer,
    PartsOrderCreateSerializer,
    DistancePricingRuleSerializer
)

class PartCategoryViewSet(viewsets.ModelViewSet):
    queryset = PartCategory.objects.filter(is_active=True)
    serializer_class = PartCategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    lookup_field = 'uuid'
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'description']

    def get_queryset(self):
        queryset = super().get_queryset()
        parent = self.request.query_params.get('parent', None)
        if parent == 'null':
            return queryset.filter(parent__isnull=True)
        elif parent:
            return queryset.filter(parent=parent)
        return queryset

class SparePartViewSet(viewsets.ModelViewSet):
    queryset = SparePart.objects.filter(is_active=True)
    lookup_field = 'uuid'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        'category': ['exact'],
        'manufacturers': ['exact'],
        'vehicle_models': ['exact'],
        'vehicle_types': ['exact'],
        'price': ['gte', 'lte'],
        'is_featured': ['exact'],
        'availability_status': ['exact']
    }
    search_fields = ['name', 'description', 'part_number']
    ordering_fields = ['price', 'created_at', 'name']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return SparePartListSerializer
        return SparePartSerializer
    
    def get_permissions(self):
        """
        Override to make only specific actions require authentication.
        Only add_to_cart and buy_now are protected, other actions are public.
        """
        if self.action in ['add_to_cart', 'buy_now', 'create', 'update', 'partial_update', 'destroy', 'upload_image', 'get_upload_params']:
            permission_classes = [permissions.IsAuthenticated]
        elif self.action == 'add_review':
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [permissions.AllowAny]
        return [permission() for permission in permission_classes]

    @action(detail=True, methods=['post'])
    def add_review(self, request, uuid=None):
        part = self.get_object()
        serializer = PartReviewSerializer(data=request.data)
        
        if serializer.is_valid():
            serializer.save(user=request.user, part=part)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def reviews(self, request, uuid=None):
        part = self.get_object()
        reviews = part.reviews.all().order_by('-created_at')
        serializer = PartReviewSerializer(reviews, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def related(self, request, uuid=None):
        part = self.get_object()
        related_parts = SparePart.objects.filter(
            category=part.category
        ).exclude(
            uuid=part.uuid
        )[:5]
        serializer = SparePartListSerializer(related_parts, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def featured(self, request):
        featured_parts = self.get_queryset().filter(is_featured=True)[:8]
        serializer = SparePartListSerializer(featured_parts, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_vehicle(self, request):
        vehicle_type = request.query_params.get('vehicle_type')
        manufacturer = request.query_params.get('manufacturer')
        model = request.query_params.get('model')
        
        queryset = self.get_queryset()
        
        if vehicle_type:
            queryset = queryset.filter(vehicle_types=vehicle_type)
        if manufacturer:
            queryset = queryset.filter(manufacturers=manufacturer)
        if model:
            queryset = queryset.filter(vehicle_models=model)
            
        serializer = SparePartListSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_to_cart(self, request, uuid=None):
        """
        Add a spare part to the user's cart.
        This is a protected endpoint that requires authentication.
        """
        part = self.get_object()
        quantity = int(request.data.get('quantity', 1))
        cart_id = request.data.get('cart_id')
        
        # Check if the part is in stock
        if part.availability_status == 'out_of_stock' or part.stock_quantity < quantity:
            return Response(
                {"detail": "This part is out of stock or has insufficient quantity."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get or create cart
        if cart_id:
            try:
                cart = PartsCart.objects.get(id=cart_id, status='active')
            except PartsCart.DoesNotExist:
                cart = PartsCart.objects.create(user=request.user)
        else:
            cart = PartsCart.objects.create(user=request.user)
        
        # Add item to cart
        cart_item, created = PartsCartItem.objects.get_or_create(
            cart=cart,
            part=part,
            defaults={'quantity': quantity}
        )
        
        if not created:
            cart_item.quantity += quantity
            cart_item.save()
        
        serializer = PartsCartSerializer(cart)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def buy_now(self, request, uuid=None):
        """
        Buy a spare part immediately, bypassing the cart.
        This is a protected endpoint that requires authentication.
        """
        part = self.get_object()
        quantity = int(request.data.get('quantity', 1))
        
        # Check if the part is in stock
        if part.availability_status == 'out_of_stock' or part.stock_quantity < quantity:
            return Response(
                {"detail": "This part is out of stock or has insufficient quantity."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create a temporary cart for direct purchase
        with transaction.atomic():
            cart = PartsCart.objects.create(user=request.user)
            PartsCartItem.objects.create(
                cart=cart,
                part=part,
                quantity=quantity
            )
            
            # Return cart info for checkout
            serializer = PartsCartSerializer(cart)
            return Response({
                "cart": serializer.data,
                "message": "Part ready for immediate checkout"
            })

    @action(detail=True, methods=['GET'])
    def get_upload_params(self, request, uuid=None):
        """Get upload parameters for spare part images"""
        part = self.get_object()
        
        params = cdn_manager.get_upload_params(
            'spare_part',
            str(part.uuid),
            {
                'allowed_formats': ['jpg', 'jpeg', 'png', 'webp'],
                'max_file_size': 5 * 1024 * 1024  # 5MB
            }
        )
        
        return Response({
            'status': 'success',
            'data': params
        })
    
    @action(detail=True, methods=['POST'])
    def upload_image(self, request, uuid=None):
        """Upload an image for a spare part"""
        part = self.get_object()
        
        try:
            # Check if image file is provided
            if 'image' not in request.FILES:
                return Response(
                    {"error": "No image file provided"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            image_file = request.FILES['image']
            is_main_image = request.data.get('is_main_image', 'false').lower() == 'true'
            
            # Upload to Cloudinary
            upload_result = cloudinary.uploader.upload(
                image_file,
                folder=f"spare_parts/{part.uuid}",
                public_id=f"{part.slug}_{timezone.now().timestamp()}",
                overwrite=True,
                resource_type="image"
            )
            
            # Update the part with the image URL
            if is_main_image:
                part.main_image = upload_result['public_id']
                part.save()
            else:
                # Add to additional images
                additional_images = part.additional_images or []
                additional_images.append({
                    'public_id': upload_result['public_id'],
                    'url': upload_result['secure_url'],
                    'created_at': timezone.now().isoformat()
                })
                part.additional_images = additional_images
                part.save()
            
            return Response({
                'status': 'success',
                'image_data': {
                    'public_id': upload_result['public_id'],
                    'url': upload_result['secure_url'],
                    'is_main_image': is_main_image
                }
            })
            
        except Exception as e:
            return Response(
                {"error": f"Failed to upload image: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# Cart management views

@api_view(['POST'])
def create_cart(request):
    """Create a new cart and associate it with the user if authenticated"""
    cart = PartsCart.objects.create(
        user=request.user if request.user.is_authenticated else None
    )
    # Store cart ID in session for anonymous users
    if not request.user.is_authenticated:
        request.session['parts_cart_id'] = cart.id
    return Response({
        "id": cart.id,
        "status": "success"
    }, status=status.HTTP_201_CREATED)

class PartsCartDetailView(generics.RetrieveAPIView):
    serializer_class = PartsCartSerializer
    permission_classes = [permissions.AllowAny]

    def get_object(self):
        cart_id = self.kwargs['cart_id']
        cart = get_object_or_404(PartsCart, id=cart_id)
        
        # Allow access if:
        # 1. Cart belongs to the authenticated user
        # 2. Cart ID matches the session cart ID for anonymous users
        # 3. Cart has no user (legacy carts)
        if (self.request.user.is_authenticated and cart.user == self.request.user) or \
           (not self.request.user.is_authenticated and str(cart_id) == str(self.request.session.get('parts_cart_id'))) or \
           (cart.user is None):
            return cart
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

class AddToCartView(generics.CreateAPIView):
    serializer_class = PartsCartItemSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        try:
            cart_id = self.kwargs['cart_id']
            cart = get_object_or_404(PartsCart, id=cart_id)
            
            # Associate cart with user if not already associated
            if request.user.is_authenticated and not cart.user:
                cart.user = request.user
                cart.save()
            elif not request.user.is_authenticated:
                request.session['parts_cart_id'] = cart.id

            # Validate required fields
            if 'part' not in request.data:
                return Response(
                    {"error": "part is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            part_uuid = request.data['part']
            quantity = int(request.data.get('quantity', 1))
            
            if quantity <= 0:
                return Response(
                    {"error": "Quantity must be greater than zero"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get part
            part = get_object_or_404(SparePart, uuid=part_uuid)
            
            # Check stock
            if part.stock_quantity < quantity:
                return Response(
                    {"error": f"Only {part.stock_quantity} units available in stock"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Add to cart
            cart_item, created = PartsCartItem.objects.get_or_create(
                cart=cart, 
                part=part,
                defaults={'quantity': quantity}
            )
            
            if not created:
                cart_item.quantity += quantity
                cart_item.save()
            
            # Return updated cart data
            serializer = PartsCartSerializer(cart)
            return Response(serializer.data)
            
        except Exception as e:
            return Response(
                {"error": f"An error occurred: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class RemoveCartItemView(generics.DestroyAPIView):
    permission_classes = [permissions.AllowAny]
    
    def delete(self, request, *args, **kwargs):
        try:
            cart_item_id = self.kwargs['cart_item_id']
            cart_item = get_object_or_404(PartsCartItem, id=cart_item_id)
            
            # Check if user has permission to remove this item
            cart = cart_item.cart
            if (request.user.is_authenticated and cart.user == request.user) or \
               (not request.user.is_authenticated and str(cart.id) == str(request.session.get('parts_cart_id'))) or \
               (cart.user is None):
                cart_item.delete()
                return Response({"status": "success"})
            else:
                return Response({"detail": "Not authorized."}, status=status.HTTP_403_FORBIDDEN)
                
        except Exception as e:
            return Response(
                {"error": f"An error occurred: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class UpdateCartItemView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request, cart_id):
        try:
            cart = get_object_or_404(PartsCart, id=cart_id)
            
            # Check permissions
            if not ((request.user.is_authenticated and cart.user == request.user) or \
                   (not request.user.is_authenticated and str(cart_id) == str(request.session.get('parts_cart_id'))) or \
                   (cart.user is None)):
                return Response({"detail": "Not authorized."}, status=status.HTTP_403_FORBIDDEN)
            
            # Get parameters
            cart_item_id = request.data.get('cart_item_id')
            quantity = request.data.get('quantity')
            
            if not cart_item_id or not quantity:
                return Response(
                    {"error": "cart_item_id and quantity are required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Convert quantity to integer
            try:
                quantity = int(quantity)
                if quantity < 1:
                    return Response(
                        {"error": "Quantity must be at least 1"}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except ValueError:
                return Response(
                    {"error": "Quantity must be a valid number"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Update the cart item
            try:
                cart_item = PartsCartItem.objects.get(id=cart_item_id, cart=cart)
                
                # Check stock
                if quantity > cart_item.part.stock_quantity:
                    return Response(
                        {"error": f"Only {cart_item.part.stock_quantity} units available in stock"}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                cart_item.quantity = quantity
                cart_item.save()
                
                # Return updated cart
                serializer = PartsCartSerializer(cart)
                return Response(serializer.data)
                
            except PartsCartItem.DoesNotExist:
                return Response(
                    {"error": "Cart item not found"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
                
        except Exception as e:
            return Response(
                {"error": f"An error occurred: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ClearCartView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def delete(self, request, cart_id):
        try:
            cart = get_object_or_404(PartsCart, id=cart_id)
            
            # Check permissions
            if not ((request.user.is_authenticated and cart.user == request.user) or \
                   (not request.user.is_authenticated and str(cart_id) == str(request.session.get('parts_cart_id'))) or \
                   (cart.user is None)):
                return Response({"detail": "Not authorized."}, status=status.HTTP_403_FORBIDDEN)
            
            # Delete all items
            cart.items.all().delete()
            
            # Return empty cart
            serializer = PartsCartSerializer(cart)
            return Response(serializer.data)
            
        except Exception as e:
            return Response(
                {"error": f"An error occurred: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class UserCartsView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get all active carts for the current user"""
        carts = PartsCart.objects.filter(user=request.user, status='active')
        serializer = PartsCartSerializer(carts, many=True)
        return Response(serializer.data)

# Order management views

class CalculateDistanceFeeView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        """Calculate delivery fee based on customer location"""
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')
        
        if not latitude or not longitude:
            return Response(
                {"error": "Latitude and longitude are required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get active pricing rule
        pricing_rule = DistancePricingRule.get_active_rule()
        if not pricing_rule:
            return Response(
                {"distance_fee": 0, "message": "No delivery fee applicable"}
            )
        
        # Calculate fee
        try:
            latitude = float(latitude)
            longitude = float(longitude)
            
            # Check if within max distance
            distance_km = pricing_rule.calculate_distance(
                pricing_rule.warehouse_latitude,
                pricing_rule.warehouse_longitude,
                latitude,
                longitude
            )
            
            if distance_km > float(pricing_rule.max_distance_km):
                return Response(
                    {
                        "error": "Location is beyond our delivery area",
                        "distance_km": distance_km,
                        "max_distance_km": float(pricing_rule.max_distance_km)
                    }, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Calculate fee
            fee = pricing_rule.calculate_charges(latitude, longitude)
            
            return Response({
                "distance_fee": fee,
                "distance_km": distance_km,
                "free_radius_km": float(pricing_rule.free_radius_km),
                "base_charge": float(pricing_rule.base_charge),
                "per_km_charge": float(pricing_rule.per_km_charge)
            })
            
        except Exception as e:
            return Response(
                {"error": f"An error occurred: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class PartsOrderViewSet(viewsets.ModelViewSet):
    """
    API endpoint for parts orders
    """
    serializer_class = PartsOrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'uuid'
    
    def get_queryset(self):
        """
        Filter orders to show only the current user's orders
        Admin users can see all orders
        """
        user = self.request.user
        if user.is_staff:
            return PartsOrder.objects.all().order_by('-created_at')
        return PartsOrder.objects.filter(user=user).order_by('-created_at')
    
    def get_serializer_class(self):
        if self.action == 'create':
            return PartsOrderCreateSerializer
        return PartsOrderSerializer
    
    def create(self, request, *args, **kwargs):
        """Create order from cart"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Get cart ID from request
        cart_id = request.data.get('cart_id')
        if not cart_id:
            return Response(
                {"error": "cart_id is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get cart
        try:
            cart = PartsCart.objects.get(id=cart_id)
            
            # Check permissions
            if not ((request.user.is_authenticated and cart.user == request.user) or \
                  (not request.user.is_authenticated and str(cart_id) == str(request.session.get('parts_cart_id'))) or \
                  (cart.user is None)):
                return Response({"detail": "Not authorized."}, status=status.HTTP_403_FORBIDDEN)
            
            # Check if cart has items
            if not cart.items.exists():
                return Response(
                    {"error": "Cart is empty"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create order
            with transaction.atomic():
                # Calculate totals
                total_amount = cart.total_price
                shipping_charges = 0
                
                # Calculate distance fee if coordinates provided
                distance_fee = 0
                latitude = serializer.validated_data.get('latitude')
                longitude = serializer.validated_data.get('longitude')
                
                if latitude and longitude:
                    pricing_rule = DistancePricingRule.get_active_rule()
                    if pricing_rule:
                        distance_fee = pricing_rule.calculate_charges(latitude, longitude)
                
                # Calculate tax (18%)
                tax_amount = total_amount * 0.18
                
                # Calculate final amount
                final_amount = total_amount + shipping_charges + tax_amount + distance_fee
                
                # Create order
                order = PartsOrder.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    customer_name=serializer.validated_data.get('customer_name') or (request.user.get_full_name() if request.user.is_authenticated else None),
                    customer_email=serializer.validated_data.get('customer_email') or (request.user.email if request.user.is_authenticated else None),
                    customer_phone=serializer.validated_data.get('customer_phone'),
                    shipping_address=serializer.validated_data.get('shipping_address'),
                    shipping_city=serializer.validated_data.get('shipping_city'),
                    shipping_state=serializer.validated_data.get('shipping_state'),
                    shipping_pincode=serializer.validated_data.get('shipping_pincode'),
                    total_amount=total_amount,
                    shipping_charges=shipping_charges,
                    tax_amount=tax_amount,
                    distance_fee=distance_fee,
                    final_amount=final_amount,
                    purchase_type=serializer.validated_data.get('purchase_type', 'cart'),
                    latitude=latitude,
                    longitude=longitude
                )
                
                # Create order items
                for cart_item in cart.items.all():
                    PartsOrderItem.objects.create(
                        order=order,
                        part=cart_item.part,
                        quantity=cart_item.quantity,
                        price=cart_item.part.get_effective_price(),
                        total=cart_item.get_total_price()
                    )
                    
                    # Update stock
                    part = cart_item.part
                    part.stock_quantity -= cart_item.quantity
                    if part.stock_quantity <= 0:
                        part.availability_status = 'out_of_stock'
                    part.save()
                
                # Mark cart as completed
                cart.status = 'completed'
                cart.save()
                
                # Return order
                response_serializer = PartsOrderSerializer(order)
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)
                
        except PartsCart.DoesNotExist:
            return Response(
                {"error": "Cart not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": f"An error occurred: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, uuid=None):
        """Cancel an order"""
        order = self.get_object()
        
        # Check if order can be cancelled
        if order.status not in ['pending', 'processing']:
            return Response(
                {"error": "Order cannot be cancelled in its current state"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Cancel order
        with transaction.atomic():
            # Return items to stock
            for item in order.items.all():
                part = item.part
                part.stock_quantity += item.quantity
                if part.stock_quantity > 0 and part.availability_status == 'out_of_stock':
                    part.availability_status = 'in_stock'
                part.save()
            
            # Update order status
            order.status = 'cancelled'
            order.save()
            
            # Return updated order
            serializer = self.get_serializer(order)
            return Response(serializer.data)

class UserOrdersView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get all orders for the current user"""
        orders = PartsOrder.objects.filter(user=request.user).order_by('-created_at')
        serializer = PartsOrderSerializer(orders, many=True)
        return Response(serializer.data) 