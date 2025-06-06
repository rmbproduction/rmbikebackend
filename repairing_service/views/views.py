from rest_framework import generics, viewsets, status
from rest_framework.generics import CreateAPIView, ListAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.permissions import AllowAny, IsAuthenticated
from ..models import Feature, ServiceCategory, Service, ServicePrice, Cart, CartItem, FieldStaff, ServiceRequest, ServiceRequestResponse, LiveLocation, DistancePricingRule, PricingPlan, AdditionalService
from ..serializers import ServicePriceSerializer, ServiceSerializer, ServiceCategorySerializer, FeatureSerializer, CartSerializer, CartItemSerializer, FieldStaffSerializer, ServiceRequestSerializer, ServiceRequestResponseSerializer, LiveLocationSerializer, PricingPlanSerializer, AdditionalServiceSerializer
from django.shortcuts import render, get_object_or_404
from vehicle.models import Manufacturer, VehicleModel, VehicleType
from vehicle.serializers import VehicleModelSerializer, ManufacturerSerializer
from accounts.models import User
import uuid
import datetime
import json
from django.http import Http404
from django.utils import timezone
from rest_framework.renderers import JSONRenderer
from django.db.models import Q
from django.db import transaction
from rest_framework import serializers

# Add this new API view for creating carts
@api_view(['POST'])
def create_cart(request):
    """Create a new cart and return its ID"""
    print(f"[DEBUG] Creating cart for user: {request.user.username if request.user.is_authenticated else 'anonymous'}")
    
    # Create the cart with user if authenticated
    cart = Cart.objects.create(
        user=request.user if request.user.is_authenticated else None,
        status='active'  # Explicitly set status to active
    )
    
    # Store cart ID in session
    request.session['cart_id'] = cart.id
    print(f"[DEBUG] Created cart with ID: {cart.id}")
    
    return Response({
        "id": cart.id,
        "status": "success",
        "message": "Cart created successfully"
    }, status=status.HTTP_201_CREATED)

class ManufacturerListView(generics.ListAPIView):
    queryset = Manufacturer.objects.all()
    serializer_class = ManufacturerSerializer
    permission_classes = [AllowAny]
    renderer_classes = [JSONRenderer]

class VehicleModelListView(generics.ListAPIView):
    serializer_class = VehicleModelSerializer
    permission_classes = [AllowAny]
    renderer_classes = [JSONRenderer]
    def get_queryset(self):
        manufacturer_id = self.request.query_params.get('manufacturer_id')
        if (manufacturer_id):
            return VehicleModel.objects.filter(manufacturer_id=manufacturer_id)
        return VehicleModel.objects.all()

class ServiceCategoryListView(generics.ListAPIView):
    queryset = ServiceCategory.objects.all()
    serializer_class = ServiceCategorySerializer
    permission_classes = [AllowAny]
    renderer_classes = [JSONRenderer]

class ServiceListByCategoryView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = ServiceSerializer
    renderer_classes = [JSONRenderer]

    def get_queryset(self):
        category_id = self.request.query_params.get('category_id')
        if category_id:
            return Service.objects.filter(category__uuid=category_id).select_related('category').prefetch_related('features')
        return Service.objects.all().select_related('category').prefetch_related('features')

class ServicePriceDetailView(generics.RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = ServicePriceSerializer
    renderer_classes = [JSONRenderer]
    
    def get_object(self):
        service_id = self.kwargs['service_id']
        manufacturer_id = self.request.query_params.get('manufacturer_id')
        vehicle_model_id = self.request.query_params.get('vehicle_model_id')
        
        try:
            # First get the service by ID
            service = Service.objects.get(id=service_id)
            
            try:
                # Then try to get the specific price for this combination
                return ServicePrice.objects.get(
                    service=service,
                    manufacturer_id=manufacturer_id,
                    vehicle_model_id=vehicle_model_id
                )
            except ServicePrice.DoesNotExist:
                # If no specific price exists, create a temporary ServicePrice object
                temp_price = ServicePrice(
                    service=service,
                    manufacturer_id=manufacturer_id,
                    vehicle_model_id=vehicle_model_id,
                    price=service.base_price
                )
                return temp_price
                
        except Service.DoesNotExist:
            raise Http404(f"Service with ID {service_id} does not exist")

class CartDetailView(generics.RetrieveAPIView):
    serializer_class = CartSerializer
    permission_classes = [AllowAny]
    renderer_classes = [JSONRenderer]
    def get_object(self):
        cart_id = self.kwargs['cart_id']
        return get_object_or_404(Cart, id=cart_id)

class RemoveCartItemView(generics.DestroyAPIView):
    permission_classes = [AllowAny]
    renderer_classes = [JSONRenderer]
    def delete(self, request, *args, **kwargs):
        cart_item_id = self.kwargs['cart_item_id']
        cart_item = get_object_or_404(CartItem, id=cart_item_id)
        cart_item.delete()
        return Response({"status": "success"})

class AddToCartView(generics.CreateAPIView):
    serializer_class = CartItemSerializer
    permission_classes = [AllowAny]
    renderer_classes = [JSONRenderer]
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
                service = Service.objects.get(id=service_id)
            except Service.DoesNotExist:
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
                            {"error": "Service not found and no service_name provided"}, 
                        status=status.HTTP_404_NOT_FOUND
                    )
            
            # Handle unique constraint by using get_or_create
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart, service=service,
                defaults={'quantity': quantity}
            )
            
            if not created:
                cart_item.quantity += quantity
                cart_item.save()
                
            # Return the updated cart data
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
    renderer_classes = [JSONRenderer]
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
    renderer_classes = [JSONRenderer]

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

class FieldStaffViewSet(viewsets.ModelViewSet):
    queryset = FieldStaff.objects.all()
    serializer_class = FieldStaffSerializer
    permission_classes = [AllowAny]
    renderer_classes = [JSONRenderer]

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
    renderer_classes = [JSONRenderer]

class AdditionalServiceListView(generics.ListAPIView):
    queryset = AdditionalService.objects.all()
    serializer_class = AdditionalServiceSerializer
    permission_classes = [AllowAny]
    renderer_classes = [JSONRenderer]

class CreateBookingView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Create a service booking from cart items or direct purchase
        
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
            "cart_id": 123,  # For cart checkout
            "service_id": 456,  # For direct purchase
            "scheduleDate": "2023-05-15",
            "scheduleTime": "14:30"
        }
        """
        try:
            # Print request body for debugging
            print(f"[DEBUG] Booking request data: {request.data}")
            
            # Determine if this is a cart checkout or direct purchase
            cart_id = request.data.get('cart_id')
            service_id = request.data.get('service_id')
            
            if not (cart_id or service_id):
                return Response(
                    {'error': 'Either cart_id or service_id is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Set purchase type based on request type
            purchase_type = ServiceRequest.PURCHASE_TYPE_CART if cart_id else ServiceRequest.PURCHASE_TYPE_DIRECT
            
            # Handle cart checkout
            if cart_id:
                cart = get_object_or_404(Cart, id=cart_id)
                cart_items = CartItem.objects.filter(cart=cart)
                
                if not cart_items.exists():
                    return Response({'error': 'Cart is empty'}, status=status.HTTP_400_BAD_REQUEST)
                
                # Calculate total amount from cart items
                service_total = sum(
                    float(item.price) * item.quantity for item in cart_items if hasattr(item, 'price') and item.price
                )
            
            # Handle direct purchase
            else:
                service = get_object_or_404(Service, id=service_id)
                service_total = float(service.base_price)
            
            # Generate a booking reference
            reference = f"RMB-{uuid.uuid4().hex[:8].upper()}"
            
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
            
            # Create service request data
            service_request_data = {
                'user': request.user,
                'customer_name': profile_data.get('name', request.user.username),
                'customer_email': profile_data.get('email', request.user.email),
                'customer_phone': profile_data.get('phone', ''),
                'address': profile_data.get('address', ''),
                'city': profile_data.get('city', ''),
                'state': profile_data.get('state', ''),
                'postal_code': profile_data.get('postalCode', ''),
                'reference': reference,
                'status': ServiceRequest.STATUS_PENDING,
                'purchase_type': purchase_type,  # Set the purchase type
                'total_amount': str(total_amount),
                'scheduled_date': scheduled_date,
                'schedule_time': scheduled_time,
                'latitude': latitude,
                'longitude': longitude,
                'distance_fee': distance_fee,
                'notes': f"{'Cart checkout' if cart_id else 'Direct purchase'} from website"
            }
            
            # Add vehicle data if available
            if vehicle_data.get('vehicle_type'):
                service_request_data['vehicle_type_id'] = vehicle_data.get('vehicle_type')
            if vehicle_data.get('manufacturer'):
                service_request_data['manufacturer_id'] = vehicle_data.get('manufacturer')
            if vehicle_data.get('model'):
                service_request_data['vehicle_model_id'] = vehicle_data.get('model')
            
            # Create the service request
            service_request = ServiceRequest.objects.create(**service_request_data)
            
            # Add services to the request
            if cart_id:
                # Add all services from cart
                for item in cart_items:
                    service_request.services.add(item.service)
                # Clear the cart after successful booking
                cart.delete()
            else:
                # Add the single service for direct purchase
                service_request.services.add(service)
            
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
    renderer_classes = [JSONRenderer]
    
    def get_queryset(self):
        service_request_id = self.kwargs['service_request_id']
        return ServiceRequestResponse.objects.filter(service_request_id=service_request_id)

class LiveLocationView(generics.RetrieveUpdateAPIView):
    serializer_class = LiveLocationSerializer
    permission_classes = [AllowAny]
    renderer_classes = [JSONRenderer]
    
    def get_object(self):
        service_request_id = self.kwargs['service_request_id']
        try:
            location = LiveLocation.objects.get(service_request_id=service_request_id)
            return location
        except LiveLocation.DoesNotExist:
            raise Http404("Live location not found for this service request")

class CalculateDistanceFeeView(APIView):
    permission_classes = [AllowAny]
    renderer_classes = [JSONRenderer]
    
    def post(self, request):
        # Extract coordinates
        try:
            user_lat = float(request.data.get('user_latitude'))
            user_lng = float(request.data.get('user_longitude'))
            provider_lat = float(request.data.get('provider_latitude', 0))
            provider_lng = float(request.data.get('provider_longitude', 0))
        except (ValueError, TypeError):
            return Response(
                {"error": "Invalid coordinates provided"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # If provider coordinates aren't provided, use shop coordinates
        # In a real app, you might get these from your app settings
        if provider_lat == 0 and provider_lng == 0:
            provider_lat = 40.7128  # Example: NYC coordinates
            provider_lng = -74.0060
            
        # Calculate distance using Haversine formula
        from math import radians, sin, cos, sqrt, atan2
        
        R = 6371  # Earth radius in kilometers
        
        # Convert coordinates from degrees to radians
        lat1 = radians(user_lat)
        lon1 = radians(user_lng)
        lat2 = radians(provider_lat)
        lon2 = radians(provider_lng)
        
        # Haversine formula
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        distance = R * c  # Distance in kilometers
        
        # Round to 2 decimal places
        distance = round(distance, 2)
        
        # Calculate fee based on distance pricing rules
        try:
            # Get applicable distance pricing rule
            pricing_rule = DistancePricingRule.objects.filter(
                min_distance__lte=distance, 
                max_distance__gte=distance
            ).first()
            
            if pricing_rule:
                # Calculate fee based on rule
                if pricing_rule.fee_type == 'FIXED':
                    fee = pricing_rule.fee_amount
                else:  # PER_KM
                    fee = pricing_rule.fee_amount * distance
                    
                # Round fee to 2 decimal places
                fee = round(fee, 2)
            else:
                # Default calculation if no matching rule
                base_fee = 5.00  # Base fee in dollars
                per_km_fee = 1.50  # Fee per kilometer
                fee = base_fee + (per_km_fee * distance)
                fee = round(fee, 2)
                
        except Exception as e:
            # Log the error and use a default calculation
            print(f"Error calculating distance fee: {str(e)}")
            fee = 5.00 + (1.50 * distance)
            fee = round(fee, 2)
            
        return Response({
            "distance": distance,
            "unit": "kilometers",
            "fee": fee,
            "currency": "USD"  # In a real app, get this from settings
        })

class UpdateCartItemView(APIView):
    permission_classes = [AllowAny]
    renderer_classes = [JSONRenderer]
    
    def post(self, request, cart_id):
        """
        Update a cart item (quantity or service)
        Request data:
        {
            "cart_item_id": 123,
            "quantity": 2,  # Optional
            "service_id": 456  # Optional
        }
        """
        try:
            cart = get_object_or_404(Cart, id=cart_id)
            
            cart_item_id = request.data.get('cart_item_id')
            if not cart_item_id:
                return Response(
                    {"error": "cart_item_id is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            cart_item = get_object_or_404(CartItem, id=cart_item_id, cart=cart)
            
            # Update quantity if provided
            quantity = request.data.get('quantity')
            if quantity is not None:
                try:
                    quantity = int(quantity)
                    if quantity <= 0:
                        # If quantity is 0 or negative, remove the item
                        cart_item.delete()
                        return Response({"status": "Item removed from cart"})
                    else:
                        cart_item.quantity = quantity
                except ValueError:
                    return Response(
                        {"error": "Invalid quantity value"}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
                    
            # Update service if provided
            service_id = request.data.get('service_id')
            if service_id:
                service = get_object_or_404(Service, id=service_id)
                cart_item.service = service
                
            # Save changes
            cart_item.save()
            
            # Return updated cart
            serializer = CartSerializer(cart)
            return Response(serializer.data)
            
        except Http404:
            return Response(
                {"error": "Cart item or service not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": f"An error occurred: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ClearCartView(APIView):
    permission_classes = [AllowAny]
    renderer_classes = [JSONRenderer]
    
    def delete(self, request, cart_id):
        """Clear all items from a cart"""
        try:
            cart = get_object_or_404(Cart, id=cart_id)
            
            # Delete all items in the cart
            cart.cartitem_set.all().delete()
            
            return Response({"status": "Cart cleared successfully"})
        except Exception as e:
            return Response(
                {"error": f"An error occurred: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class CancelBookingView(APIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [JSONRenderer]
    
    def post(self, request, booking_id):
        try:
            # Get the booking
            booking = get_object_or_404(ServiceRequest, id=booking_id, user=request.user)
            
            # Check if the booking is already cancelled
            if booking.status == ServiceRequest.STATUS_CANCELLED:
                return Response({
                    "status": "error",
                    "message": "Booking is already cancelled."
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Cancel the booking
            success = booking.cancel_service(request.user)
            
            if not success:
                return Response({
                    "status": "error",
                    "message": "Cannot cancel this booking due to its current status."
                }, status=status.HTTP_400_BAD_REQUEST)
            
            return Response({
                "status": "success",
                "message": "Booking has been cancelled successfully."
            })
            
        except Exception as e:
            return Response({
                "status": "error",
                "message": f"An error occurred: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ClearCancelledBookingsView(APIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [JSONRenderer]
    
    def post(self, request):
        try:
            # Get all cancelled bookings for the current user
            cancelled_bookings = ServiceRequest.objects.filter(
                user=request.user,
                status=ServiceRequest.STATUS_CANCELLED,
                hidden=False  # Only get bookings that aren't already hidden
            )
            
            # Mark them as hidden
            count = cancelled_bookings.count()
            if count > 0:
                cancelled_bookings.update(hidden=True)
                
                return Response({
                    "status": "success",
                    "message": f"Successfully cleared {count} cancelled booking(s).",
                    "count": count
                })
            else:
                return Response({
                    "status": "success",
                    "message": "No cancelled bookings to clear.",
                    "count": 0
                })
            
        except Exception as e:
            return Response({
                "status": "error",
                "message": f"An error occurred: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UserBookingsView(APIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [JSONRenderer]
    
    def get(self, request):
        """Get all bookings for the authenticated user"""
        try:
            # Get all service requests for the user
            bookings = ServiceRequest.objects.filter(user=request.user).order_by('-created_at')
            
            # Define status display mapping
            status_display_mapping = {
                'pending': 'Pending',
                'confirmed': 'Confirmed',
                'scheduled': 'Scheduled',
                'in_progress': 'In Progress',
                'completed': 'Completed',
                'cancelled': 'Cancelled',
                'rejected': 'Rejected'
            }
            
            # Prepare the response data
            data = []
            for booking in bookings:
                # Get services for this booking
                services = booking.services.all()
                service_data = []
                
                # Calculate the actual service total
                service_total = 0
                
                for service in services:
                    service_price = service.base_price
                    service_data.append({
                        'id': service.id,
                        'name': service.name,
                        'quantity': 1,  # Default quantity
                        'price': str(service_price)
                    })
                    service_total += float(service_price)
                
                # Add vehicle data if available
                vehicle_data = None
                try:
                    if booking.vehicle_type_id and booking.manufacturer_id and booking.vehicle_model_id:
                        # Get the actual model instances
                        vehicle_type = VehicleType.objects.get(id=booking.vehicle_type_id)
                        manufacturer = Manufacturer.objects.get(id=booking.manufacturer_id)
                        vehicle_model = VehicleModel.objects.get(id=booking.vehicle_model_id)
                        
                        vehicle_data = {
                            'vehicle_type': booking.vehicle_type_id,
                            'manufacturer': booking.manufacturer_id,
                            'model': booking.vehicle_model_id,
                            'vehicle_type_name': vehicle_type.name,
                            'manufacturer_name': manufacturer.name,
                            'model_name': vehicle_model.name
                        }
                except Exception as e:
                    print(f"[WARNING] Error fetching vehicle data for booking {booking.id}: {str(e)}")
                    # If there's an error, still provide the IDs without names
                    if booking.vehicle_type_id and booking.manufacturer_id and booking.vehicle_model_id:
                        vehicle_data = {
                            'vehicle_type': booking.vehicle_type_id,
                            'manufacturer': booking.manufacturer_id,
                            'model': booking.vehicle_model_id
                        }
                
                # Ensure total_amount is properly calculated if it's zero
                total_amount = booking.total_amount
                if float(total_amount) == 0 and service_total > 0:
                    # If total_amount is zero but services have prices, use service total
                    total_amount = service_total
                    # Also update the booking in the database
                    booking.total_amount = total_amount
                    booking.save(update_fields=['total_amount'])
                
                # Create booking data object
                booking_data = {
                    'id': booking.id,
                    'reference': booking.reference or f'RMB-{uuid.uuid4().hex[:8].upper()}',
                    'created_at': booking.created_at.isoformat(),
                    'status': booking.status,
                    'status_display': status_display_mapping.get(booking.status.lower(), booking.status),
                    'total_amount': str(total_amount),
                    'schedule_date': booking.scheduled_date.isoformat() if booking.scheduled_date else None,
                    'schedule_time': booking.schedule_time.strftime('%H:%M') if booking.schedule_time else None,
                    'services': service_data,
                    'address': booking.address
                }
                
                if vehicle_data:
                    booking_data['vehicle'] = vehicle_data
                    
                data.append(booking_data)
            
            return Response(data, status=status.HTTP_200_OK)
            
        except Exception as e:
            print(f"[ERROR] Failed to retrieve user bookings: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class GetServiceNowView(APIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [JSONRenderer]
    
    def post(self, request):
        """
        Create a direct service booking without cart
        
        Expected data:
        {
            "service_id": 1,  # Integer ID
            "profile": {
                "name": "Customer Name",
                "email": "customer@example.com",
                "phone": "9876543210",
                "address": "123 Customer Street",
                "city": "City",
                "state": "State",
                "postalCode": "123456"
            },
            "vehicle": {
                "vehicle_type": 1,
                "manufacturer": 1,
                "model": 1
            },
            "scheduleDate": "2024-03-20",
            "scheduleTime": "14:30",
            "latitude": 12.345678,
            "longitude": 78.901234,
            "distanceFee": 10.00
        }
        """
        try:
            # Print request body for debugging
            print(f"[DEBUG] Direct booking request data: {request.data}")
            
            # Get and validate service_id as integer
            try:
                service_id = int(request.data.get('service_id'))
            except (TypeError, ValueError):
                return Response(
                    {'error': 'service_id must be a valid integer'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not service_id:
                return Response(
                    {'error': 'Service ID is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                service = Service.objects.get(id=service_id)
            except Service.DoesNotExist:
                return Response(
                    {'error': f'Service with ID {service_id} not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Generate a booking reference
            reference = f"RMB-{uuid.uuid4().hex[:8].upper()}"
            
            # Calculate service price
            service_price = float(service.base_price)
            
            # Get location and distance fee data
            latitude = request.data.get('latitude')
            longitude = request.data.get('longitude')
            distance_fee = request.data.get('distanceFee', 0)
            
            # Calculate total with distance fee
            total_amount = service_price + float(distance_fee)
            
            # Get user profile and schedule data
            profile_data = request.data.get('profile', {})
            vehicle_data = request.data.get('vehicle', {})
            scheduled_date = request.data.get('scheduleDate')
            scheduled_time = request.data.get('scheduleTime')
            
            # Parse date and time if provided
            parsed_date = None
            if scheduled_date:
                try:
                    parsed_date = datetime.datetime.strptime(scheduled_date, '%Y-%m-%d').date()
                except ValueError:
                    return Response(
                        {"error": "Invalid scheduleDate format. Please use YYYY-MM-DD format."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                parsed_date = datetime.date.today() + datetime.timedelta(days=2)
            
            # Parse time if provided
            parsed_time = None
            if scheduled_time:
                try:
                    parsed_time = datetime.datetime.strptime(scheduled_time, '%H:%M').time()
                except ValueError:
                    return Response(
                        {"error": "Invalid scheduleTime format. Please use HH:MM format."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Create service request data
            service_request_data = {
                'user': request.user,
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
                'schedule_time': parsed_time,
                'latitude': latitude,
                'longitude': longitude,
                'distance_fee': distance_fee,
                'notes': f"Direct booking for {service.name}"
            }
            
            # Add vehicle data if available
            if vehicle_data.get('vehicle_type'):
                service_request_data['vehicle_type_id'] = vehicle_data.get('vehicle_type')
            if vehicle_data.get('manufacturer'):
                service_request_data['manufacturer_id'] = vehicle_data.get('manufacturer')
            if vehicle_data.get('model'):
                service_request_data['vehicle_model_id'] = vehicle_data.get('model')
            
            # Create the service request
            service_request = ServiceRequest.objects.create(**service_request_data)
            
            # Add the service
            service_request.services.add(service)
            
            # Return the booking details
            response_data = ServiceRequestSerializer(service_request).data
            response_data['message'] = "Direct booking created successfully. Our service experts will contact you shortly."
            return Response(response_data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            print(f"[ERROR] Direct booking creation failed: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CancelServiceNowView(APIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [JSONRenderer]
    
    def post(self, request, service_request_id):
        """
        Cancel a direct service booking
        
        URL Parameters:
        - service_request_id: The ID of the service request to cancel
        """
        try:
            # Get the service request and verify ownership
            service_request = get_object_or_404(
                ServiceRequest, 
                id=service_request_id,
                user=request.user
            )
            
            # Check if it's already cancelled
            if service_request.status == 'cancelled':
                return Response({
                    "status": "error",
                    "message": "This service request is already cancelled."
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if it can be cancelled (not in progress or completed)
            if service_request.status in ['in_progress', 'completed']:
                return Response({
                    "status": "error",
                    "message": f"Cannot cancel a service request that is {service_request.status}."
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get cancellation reason if provided
            cancellation_reason = request.data.get('reason', 'Cancelled by user')
            
            # Cancel the service request
            service_request.status = 'cancelled'
            service_request.notes = (
                f"{service_request.notes}\n"
                f"Cancelled on {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"Reason: {cancellation_reason}"
            ).strip()
            service_request.save()
            
            # Return success response with updated service request details
            return Response({
                "status": "success",
                "message": "Service request cancelled successfully.",
                "service_request": {
                    "id": service_request.id,
                    "reference": service_request.reference,
                    "status": "cancelled",
                    "cancelled_at": timezone.now().isoformat(),
                    "reason": cancellation_reason
                }
            }, status=status.HTTP_200_OK)
            
        except Http404:
            return Response({
                "status": "error",
                "message": "Service request not found or you don't have permission to cancel it."
            }, status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            print(f"[ERROR] Failed to cancel service request: {str(e)}")
            return Response({
                "status": "error",
                "message": "An error occurred while cancelling the service request."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CartItemSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source='service.name')
    service_price = serializers.DecimalField(source='service.base_price', max_digits=10, decimal_places=2)
    
    class Meta:
        model = CartItem
        fields = ['id', 'service_id', 'quantity', 'service_name', 'service_price']

class DetailedCartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(source='cartitem_set', many=True)
    total_amount = serializers.SerializerMethodField()
    total_items = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ['id', 'user', 'created_at', 'modified_at', 'status', 'items', 'total_amount', 'total_items']

    def get_total_amount(self, obj):
        total = sum(item.service.base_price * item.quantity for item in obj.cartitem_set.all())
        return str(total)

    def get_total_items(self, obj):
        return obj.cartitem_set.count()

class UserCartsView(APIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [JSONRenderer]

    def get(self, request):
        """Get all carts for the current user"""
        print(f"[DEBUG] Getting carts for user: {request.user.username}")
        print(f"[DEBUG] Session cart_id: {request.session.get('cart_id')}")
        
        # Get all carts for the user
        user_carts = Cart.objects.filter(user=request.user)
        print(f"[DEBUG] Found {user_carts.count()} user carts")
        
        # Get session cart if it exists
        session_cart_id = request.session.get('cart_id')
        if session_cart_id:
            session_cart = Cart.objects.filter(id=session_cart_id)
            if session_cart.exists():
                # Combine querysets if session cart exists
                user_carts = user_carts | session_cart
        
        # Order by created_at
        user_carts = user_carts.order_by('-created_at')
        print(f"[DEBUG] Total carts after combining: {user_carts.count()}")
        
        serializer = DetailedCartSerializer(user_carts, many=True)
        return Response(serializer.data)