from rest_framework import generics, viewsets, status
from rest_framework.generics import CreateAPIView, ListAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.permissions import AllowAny, IsAuthenticated
from .models import Feature, ServiceCategory, Service, ServicePrice, Cart, CartItem, FieldStaff, ServiceRequest, ServiceRequestResponse, LiveLocation, DistancePricingRule, PricingPlan, AdditionalService
from .serializers import ServicePriceSerializer, ServiceSerializer, ServiceCategorySerializer, FeatureSerializer, CartSerializer, CartItemSerializer, FieldStaffSerializer, ServiceRequestSerializer, ServiceRequestResponseSerializer, LiveLocationSerializer, PricingPlanSerializer, AdditionalServiceSerializer
from django.shortcuts import render, get_object_or_404
from vehicle.models import Manufacturer, VehicleModel
from vehicle.serializers import VehicleModelSerializer, ManufacturerSerializer
from accounts.models import User
import uuid
import datetime
import json
from django.http import Http404
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.db.models import Q

# Add this new API view for creating carts
@api_view(['POST'])
def create_cart(request):
    """Create a new cart and return its ID"""
    cart = Cart.objects.create()
    return Response({"id": cart.id, "status": "success"}, status=status.HTTP_201_CREATED)

class ManufacturerListView(generics.ListAPIView):
    queryset = Manufacturer.objects.all()
    serializer_class = ManufacturerSerializer
    permission_classes = [AllowAny]

class VehicleModelListView(generics.ListAPIView):
    serializer_class = VehicleModelSerializer
    permission_classes = [AllowAny]
    def get_queryset(self):
        manufacturer_id = self.request.query_params.get('manufacturer_id')
        if (manufacturer_id):
            return VehicleModel.objects.filter(manufacturer_id=manufacturer_id)
        return VehicleModel.objects.all()

class ServiceCategoryListView(generics.ListAPIView):
    queryset = ServiceCategory.objects.all()
    serializer_class = ServiceCategorySerializer
    permission_classes = [AllowAny]

class ServiceListByCategoryView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = ServiceSerializer

    def get_queryset(self):
        category_id = self.request.query_params.get('category_id')
        if category_id:
            return Service.objects.filter(category_id=category_id).select_related('category').prefetch_related('features')
        return Service.objects.all().select_related('category').prefetch_related('features')

class ServicePriceDetailView(generics.RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = ServicePriceSerializer
    
    def get_object(self):
        service_id = self.kwargs['service_id']
        manufacturer_id = self.request.query_params.get('manufacturer_id')
        vehicle_model_id = self.request.query_params.get('vehicle_model_id')
        
        try:
            # Try to get the specific price for this combination
            return ServicePrice.objects.get(
                service_id=service_id, 
                manufacturer_id=manufacturer_id, 
                vehicle_model_id=vehicle_model_id
            )
        except ServicePrice.DoesNotExist:
            # If no specific price exists, get the base service and create a
            # temporary ServicePrice object with the base price
            try:
                service = Service.objects.get(id=service_id)
                temp_price = ServicePrice(
                    service=service,
                    manufacturer_id=manufacturer_id,
                    vehicle_model_id=vehicle_model_id,
                    price=service.base_price
                )
                return temp_price
            except Service.DoesNotExist:
                # If the service doesn't exist, return 404
                raise Http404(f"Service with ID {service_id} does not exist")

class CartDetailView(generics.RetrieveAPIView):
    serializer_class = CartSerializer
    permission_classes = [AllowAny]
    def get_object(self):
        cart_id = self.kwargs['cart_id']
        return get_object_or_404(Cart, id=cart_id)

class RemoveCartItemView(generics.DestroyAPIView):
    permission_classes = [AllowAny]
    def delete(self, request, *args, **kwargs):
        try:
            cart_item_id = self.kwargs['cart_item_id']
            cart_item = get_object_or_404(CartItem, id=cart_item_id)
            cart_item.delete()
            return Response({"status": "success"})
        except Exception as e:
            return Response(
                {"error": f"An error occurred: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class AddToCartView(generics.CreateAPIView):
    serializer_class = CartItemSerializer
    permission_classes = [AllowAny]
    def create(self, request, *args, **kwargs):
        try:
            cart_id = self.kwargs['cart_id']
            cart = get_object_or_404(Cart, id=cart_id)
            
            # Validate required fields
            if 'service_id' not in request.data:
                return Response(
                    {"error": "service_id is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            service_id = request.data['service_id']
            quantity = int(request.data.get('quantity', 1))
            
            if quantity <= 0:
                return Response(
                    {"error": "Quantity must be greater than zero"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                # Try to get service by ID
                service = get_object_or_404(Service, id=service_id)
            except Http404:
                # If service doesn't exist but we have a name, create a temporary one
                if 'service_name' in request.data:
                    service_name = request.data['service_name']
                    # Get or create a category for temporary services
                    category, _ = ServiceCategory.objects.get_or_create(
                        name="Temporary Category", 
                        defaults={"slug": "temporary-category"}
                    )
                    # Create temporary service
                    service = Service.objects.create(
                        name=service_name,
                        base_price="0.00",  # Default price
                        category=category
                    )
                else:
                    return Response(
                        {"error": "Service not found"}, 
                        status=status.HTTP_404_NOT_FOUND
                    )
            
            cart_item, created = CartItem.objects.get_or_create(cart=cart, service=service)
            if not created:
                cart_item.quantity += int(quantity)
                cart_item.save()
            
            # Return updated cart data
            serializer = CartSerializer(cart)
            return Response({
                "status": "success", 
                "cart_item_id": cart_item.id,
                "cart": serializer.data
            })
        except ValueError as e:
            return Response(
                {"error": f"Invalid value: {str(e)}"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": f"An error occurred: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class CartItemCreateView(CreateAPIView):
    serializer_class = CartItemSerializer
    permission_classes = [AllowAny]
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

class ServiceRequestViewSet(viewsets.ModelViewSet):
    queryset = ServiceRequest.objects.all()
    serializer_class = ServiceRequestSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        serializer.save()

    def respond_to_request(self, request, pk=None):
        service_request = self.get_object()
        serializer = ServiceRequestResponseSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(service_request=service_request, field_staff=request.user.fieldstaff)
            return Response(serializer.data)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def start_tracking(self, request, pk=None):
        service_request = self.get_object()
        service_request.start_tracking(request.user.fieldstaff, request.data['latitude'], request.data['longitude'])
        return Response({'status': 'tracking started'})

    def update_location(self, request, pk=None):
        service_request = self.get_object()
        service_request.update_location(request.user.fieldstaff, request.data['latitude'], request.data['longitude'])
        return Response({'status': 'location updated'})

    def complete_service(self, request, pk=None):
        service_request = self.get_object()
        service_request.complete_service(request.user.fieldstaff, request.data['service_cost'])
        return Response({'status': 'service completed'})

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """
        Cancel a service request
        """
        service_request = self.get_object()
        if service_request.cancel_service(request.user):
            return Response({'status': 'cancelled'})
        return Response(
            {'error': 'Service cannot be cancelled'}, 
            status=status.HTTP_400_BAD_REQUEST
        )

class FieldStaffViewSet(viewsets.ModelViewSet):
    queryset = FieldStaff.objects.all()
    serializer_class = FieldStaffSerializer
    permission_classes = [AllowAny]

    def current_location(self, request, pk=None):
        field_staff = self.get_object()
        serializer = LiveLocationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(field_staff=field_staff)
            return Response(serializer.data)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PricingPlanListView(generics.ListAPIView):
    queryset = PricingPlan.objects.all()
    serializer_class = PricingPlanSerializer
    permission_classes = [AllowAny]

class AdditionalServiceListView(generics.ListAPIView):
    queryset = AdditionalService.objects.all()
    serializer_class = AdditionalServiceSerializer
    permission_classes = [AllowAny]

class CreateBookingView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Create a service booking from cart items
        
        Expected data:
        {
            "profile": {
                "name": "Customer Name",
                "email": "customer@example.com",
                "phone": "9876543210",
                "address": "123 Customer Street",
                ...
            },
            "vehicle": {
                "vehicle_type": 1,
                "manufacturer": 2,
                "model": 3
            },
            "cart_id": 123,
            "services": [
                {"id": 1, "quantity": 1},
                {"id": 2, "quantity": 2}
            ],
            "scheduleDate": "2023-05-15",
            "scheduleTime": "14:30"
        }
        """
        try:
            # Print request body for debugging
            print(f"[DEBUG] Booking request data: {request.data}")
            
            # Get cart data
            cart_id = request.data.get('cart_id')
            if not cart_id:
                return Response({'error': 'Cart ID is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            cart = get_object_or_404(Cart, id=cart_id)
            cart_items = CartItem.objects.filter(cart=cart)
            
            if not cart_items.exists():
                return Response({'error': 'Cart is empty'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Generate a booking reference
            reference = f"RMB-{uuid.uuid4().hex[:8].upper()}"
            
            # Calculate total amount (service total)
            service_total = sum(
                float(item.price) * item.quantity for item in cart_items if hasattr(item, 'price') and item.price
            )
            
            # Get location and distance fee data
            latitude = request.data.get('latitude')
            longitude = request.data.get('longitude')
            distance_fee = request.data.get('distanceFee', 0)
            
            # Calculate total with distance fee
            total_amount = service_total + float(distance_fee)
            
            # Get user profile and schedule data
            profile_data = request.data.get('profile', {})
            vehicle_data = request.data.get('vehicle', {})
            scheduled_date = request.data.get('scheduleDate') or profile_data.get('scheduleDate')
            scheduled_time = request.data.get('scheduleTime') or profile_data.get('scheduleTime')
            
            # Print debugging information
            print(f"[DEBUG] Profile data: {profile_data}")
            print(f"[DEBUG] Vehicle data: {vehicle_data}")
            print(f"[DEBUG] Scheduled date: {scheduled_date}")
            print(f"[DEBUG] Scheduled time: {scheduled_time}")
            print(f"[DEBUG] Location: {latitude}, {longitude}")
            print(f"[DEBUG] Distance fee: {distance_fee}")

            # Parse date and time if provided
            parsed_date = None
            if scheduled_date:
                try:
                    parsed_date = datetime.datetime.strptime(scheduled_date, '%Y-%m-%d').date()
                    print(f"[DEBUG] Parsed date: {parsed_date}")
                except ValueError:
                    print(f"[DEBUG] Failed to parse date: {scheduled_date}")
                    parsed_date = datetime.date.today() + datetime.timedelta(days=2)
            else:
                parsed_date = datetime.date.today() + datetime.timedelta(days=2)
            
            # Create a service request object
            creation_data = {
                'user_id': request.user.id,
                'customer_name': profile_data.get('name', request.user.username),
                'customer_email': profile_data.get('email', request.user.email),
                'customer_phone': profile_data.get('phone', ''),
                'address': profile_data.get('address', ''),
                'city': profile_data.get('city', ''),
                'state': profile_data.get('state', ''),
                'postal_code': profile_data.get('postalCode', ''),
                'reference': reference,
                'status': 'pending',
                'total_amount': str(total_amount),
                'scheduled_date': parsed_date,
                'latitude': latitude,
                'longitude': longitude,
                'distance_fee': distance_fee,
                'notes': f"Services: {', '.join([item.service.name for item in cart_items])}"
            }
            
            # Add vehicle data if available
            if vehicle_data.get('vehicle_type'):
                creation_data['vehicle_type_id'] = vehicle_data.get('vehicle_type')
            if vehicle_data.get('manufacturer'):
                creation_data['manufacturer_id'] = vehicle_data.get('manufacturer')
            if vehicle_data.get('model'):
                creation_data['vehicle_model_id'] = vehicle_data.get('model')
                
            # Add scheduled time if provided
            if scheduled_time:
                try:
                    # Try parsing the time
                    time_obj = datetime.datetime.strptime(scheduled_time, '%H:%M').time()
                    creation_data['schedule_time'] = time_obj
                    print(f"[DEBUG] Parsed time: {time_obj}")
                except ValueError:
                    print(f"[DEBUG] Failed to parse time: {scheduled_time}")
            
            # Remove unexpected fields that might cause errors
            unexpected_fields = ['customer', 'service_location', 'additional_notes', 'scheduled_time']
            for field in unexpected_fields:
                if field in creation_data:
                    del creation_data[field]
            
            # Create the service request
            service_request = ServiceRequest.objects.create(**creation_data)
            
            # Add service request items
            for item in cart_items:
                service_request.services.add(item.service)
            
            # Clear the cart
            cart.delete()
            
            # Return the booking details
            response_data = ServiceRequestSerializer(service_request).data
            response_data['message'] = "Booking created successfully. Our service experts will contact you shortly."
            return Response(response_data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            print(f"[ERROR] Booking creation failed: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ServiceRequestResponseDetailView(generics.ListCreateAPIView):
    serializer_class = ServiceRequestResponseSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        service_request_id = self.kwargs['service_request_id']
        return ServiceRequestResponse.objects.filter(service_request_id=service_request_id)

class LiveLocationView(generics.RetrieveUpdateAPIView):
    serializer_class = LiveLocationSerializer
    permission_classes = [AllowAny]
    
    def get_object(self):
        service_request_id = self.kwargs['service_request_id']
        try:
            return LiveLocation.objects.get(service_request_id=service_request_id)
        except LiveLocation.DoesNotExist:
            raise Http404("Location not found")

# Add this at the end of the file
class CalculateDistanceFeeView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        """
        Calculate distance-based fees based on customer location
        
        This feature is currently disabled. Returns a fixed value of 0.
        """
        # Return a fixed response to avoid errors
        return Response({
            "distance": 0,
            "fee": 0,
            "within_free_radius": True,
            "free_radius_km": 5.00,
            "base_charge": 0,
            "per_km_charge": 0
        })
        
        # Original implementation commented out
        """
        try:
            # Extract coordinates from request
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
                # If no rule exists, return zero fee
                return Response({
                    "distance": 0,
                    "fee": 0,
                    "within_free_radius": True
                })
            
            # Calculate distance and fee
            distance = pricing_rule.calculate_distance(
                pricing_rule.service_center_latitude, 
                pricing_rule.service_center_longitude,
                float(latitude), 
                float(longitude)
            )
            
            # Determine if within free radius
            within_free_radius = distance <= float(pricing_rule.free_radius_km)
            
            # Calculate fee if outside free radius
            fee = 0
            if not within_free_radius:
                extra_distance = distance - float(pricing_rule.free_radius_km)
                fee = float(pricing_rule.base_charge) + (extra_distance * float(pricing_rule.per_km_charge))
            
            # Return response
            return Response({
                "distance": distance,
                "fee": fee,
                "within_free_radius": within_free_radius,
                "free_radius_km": float(pricing_rule.free_radius_km),
                "base_charge": float(pricing_rule.base_charge),
                "per_km_charge": float(pricing_rule.per_km_charge)
            })
            
        except Exception as e:
            print(f"[ERROR] Distance fee calculation failed: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        """

# Add this after AddToCartView
class UpdateCartItemView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request, cart_id):
        """
        Update the quantity of an item in the cart
        
        Expected data:
        {
            "cart_item_id": 1,
            "quantity": 3
        }
        """
        try:
            cart_item_id = request.data.get('cart_item_id')
            quantity = request.data.get('quantity')
            
            if not cart_item_id or not quantity:
                return Response(
                    {"error": "Cart item ID and quantity are required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            # Verify that the cart item belongs to the specified cart
            cart_item = get_object_or_404(CartItem, id=cart_item_id, cart_id=cart_id)
            
            # Update the quantity
            cart_item.quantity = int(quantity)
            cart_item.save()
            
            return Response({
                "status": "success",
                "cart_item_id": cart_item.id,
                "quantity": cart_item.quantity
            })
            
        except Exception as e:
            print(f"[ERROR] Failed to update cart item: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ClearCartView(APIView):
    permission_classes = [AllowAny]
    
    def delete(self, request, cart_id):
        """
        Remove all items from a cart
        """
        try:
            # Verify the cart exists
            cart = get_object_or_404(Cart, id=cart_id)
            
            # Remove all items from the cart
            CartItem.objects.filter(cart=cart).delete()
            
            return Response({"status": "success", "message": "All items removed from cart"})
            
        except Exception as e:
            print(f"[ERROR] Failed to clear cart: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UserBookingsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get all service bookings for the current user"""
        try:
            # Get user's bookings, excluding hidden ones
            bookings = ServiceRequest.objects.filter(
                user=request.user,
                hidden=False
            ).order_by('-created_at')
            
            # Create serializer with many=True to handle multiple bookings
            serializer = ServiceRequestSerializer(bookings, many=True)
            
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
