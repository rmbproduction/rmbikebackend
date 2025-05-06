from decimal import Decimal
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated,AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from authback.permissions import IsOwnerOrStaff, IsStaffOrReadOnly
from .models import Vehicle, SellRequest, InspectionReport, PurchaseOffer, VehiclePurchase, VehicleBooking
from .serializers import (
    VehicleSerializer, SellRequestSerializer, 
    InspectionReportSerializer, PurchaseOfferSerializer,
    VehiclePurchaseSerializer, VehicleBookingSerializer
)
from rest_framework.exceptions import PermissionDenied
from django.contrib.auth.models import User
from .models import Notification
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
import base64
import json

class VehicleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Vehicle model with advanced filtering and search capabilities
    """
    queryset = Vehicle.objects.all()
    serializer_class = VehicleSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    permission_classes = [AllowAny]
    # Filterable fields
    filterset_fields = {
        'vehicle_type': ['exact'],
        'brand': ['exact', 'in'],
        'model': ['exact', 'in'],
        'year': ['exact', 'gte', 'lte'],
        'fuel_type': ['exact'],
        'status': ['exact', 'in'],
        'price': ['gte', 'lte'],
        'emi_available': ['exact'],
        'registration_number': ['exact', 'icontains'],
    }
    
    # Searchable fields
    search_fields = ['brand', 'model', 'registration_number', 'features', 'highlights']
    
    # Orderable fields
    ordering_fields = ['price', 'year', 'kms_driven', 'created_at']
    ordering = ['-created_at']  # Default ordering

    def get_queryset(self):
        """
        Enhance queryset with additional filtering options
        """
        queryset = super().get_queryset()
        
        # Registration number exact match filter
        registration_number = self.request.query_params.get('registration_number')
        if registration_number:
            queryset = queryset.filter(registration_number__iexact=registration_number)
        
        # Price range filter
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        if min_price:
            queryset = queryset.filter(price__gte=Decimal(min_price))
        if max_price:
            queryset = queryset.filter(price__lte=Decimal(max_price))
        
        # Kilometer range filter
        min_kms = self.request.query_params.get('min_kms')
        max_kms = self.request.query_params.get('max_kms')
        if min_kms:
            queryset = queryset.filter(kms_driven__gte=int(min_kms))
        if max_kms:
            queryset = queryset.filter(kms_driven__lte=int(max_kms))
        
        # Feature filter
        features = self.request.query_params.getlist('features')
        if features:
            for feature in features:
                queryset = queryset.filter(features__contains=[feature])
        
        return queryset

    @action(detail=False, methods=['get'])
    def check_registration_number(self, request):
        """
        Check if a registration number already exists
        """
        registration_number = request.query_params.get('registration_number', '')
        if not registration_number:
            return Response(
                {"detail": "Registration number is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Normalize the registration number (uppercase, remove spaces)
        normalized_reg_number = registration_number.upper().replace(' ', '')
        
        # Check if it exists
        exists = Vehicle.objects.filter(
            registration_number__iexact=normalized_reg_number
        ).exists()
        
        return Response({"exists": exists})

    @action(detail=False, methods=['get'])
    def filters(self):
        """
        Return available filter options for the frontend
        """
        vehicles = self.get_queryset()
        return Response({
            'brands': vehicles.values_list('brand', flat=True).distinct(),
            'models': vehicles.values_list('model', flat=True).distinct(),
            'vehicle_types': dict(Vehicle.VehicleType.choices),
            'fuel_types': dict(Vehicle.FuelType.choices),
            'year_range': {
                'min': vehicles.order_by('year').values_list('year', flat=True).first(),
                'max': vehicles.order_by('-year').values_list('year', flat=True).first(),
            },
            'price_range': {
                'min': vehicles.order_by('price').values_list('price', flat=True).first(),
                'max': vehicles.order_by('-price').values_list('price', flat=True).first(),
            },
            'kms_range': {
                'min': vehicles.order_by('kms_driven').values_list('kms_driven', flat=True).first(),
                'max': vehicles.order_by('-kms_driven').values_list('kms_driven', flat=True).first(),
            }
        })

    @action(detail=False, methods=['get'])
    def featured(self):
        """
        Return featured vehicles (e.g., best deals, newly added)
        """
        # Get available vehicles with complete information
        available = self.get_queryset().filter(
            status=Vehicle.Status.AVAILABLE,
            images__has_key='thumbnail'
        ).exclude(price=0)

        # Get best deals (lowest price for their category)
        best_deals = available.order_by('vehicle_type', 'price').distinct('vehicle_type')[:5]
        
        # Get newly added vehicles
        new_arrivals = available.order_by('-created_at')[:5]
        
        return Response({
            'best_deals': VehicleSerializer(best_deals, many=True).data,
            'new_arrivals': VehicleSerializer(new_arrivals, many=True).data
        })

    @action(detail=True, methods=['get'])
    def similar(self, request, pk=None):
        """
        Return similar vehicles based on type, price range, and brand
        """
        vehicle = self.get_object()
        price_range = (vehicle.price * Decimal('0.8'), vehicle.price * Decimal('1.2'))
        
        similar = self.get_queryset().filter(
            Q(vehicle_type=vehicle.vehicle_type) |
            Q(brand=vehicle.brand),
            price__range=price_range,
            status=Vehicle.Status.AVAILABLE
        ).exclude(id=vehicle.id)[:5]
        
        return Response(VehicleSerializer(similar, many=True).data)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=['post'])
    def buy(self, request, pk=None):
        """Initiate purchase of a vehicle"""
        vehicle = self.get_object()
        
        if vehicle.status != 'available':
            return Response(
                {"detail": "This vehicle is not available for purchase"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = VehiclePurchaseSerializer(
            data={
                'vehicle': vehicle.id,
                'amount': vehicle.price,
                'delivery_address': request.data.get('delivery_address'),
                'contact_number': request.data.get('contact_number'),
                'payment_method': request.data.get('payment_method'),
                'notes': request.data.get('notes', '')
            },
            context={'request': request}
        )
        
        if serializer.is_valid():
            with transaction.atomic():
                purchase = serializer.save()
                vehicle.status = 'pending_sale'
                vehicle.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def book(self, request, pk=None):
        """Book a vehicle"""
        vehicle = self.get_object()
        
        # Always allow booking even if is_bookable returns false
        # Just log that the vehicle is not in the ideal state
        if not vehicle.is_bookable():
            print(f"Warning: Vehicle {vehicle.id} is being booked but is in {vehicle.status} status")
        
        # Validate the contact number format
        contact_number = request.data.get('contact_number', '')
        if not contact_number:
            return Response(
                {"detail": "Contact number is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Simple validation for phone number
        if not (10 <= len(contact_number.replace('+', '').replace('-', '').replace(' ', '')) <= 15):
            return Response(
                {"detail": "Contact number must be 10-15 digits with optional + prefix"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = VehicleBookingSerializer(
            data={
                'vehicle': vehicle.id,
                'contact_number': contact_number,
                'notes': request.data.get('notes', '')
            },
            context={'request': request}
        )
        
        if serializer.is_valid():
            booking = serializer.save()
            return Response(
                {
                    "detail": f"Vehicle {vehicle.brand} {vehicle.model} booked successfully. Our team will contact you shortly.",
                    "booking": VehicleBookingSerializer(booking).data
                }, 
                status=status.HTTP_201_CREATED
            )
        
        # Format validation errors to be more user-friendly
        errors = serializer.errors
        error_message = "Validation error"
        
        if 'contact_number' in errors:
            error_message = f"Contact number error: {errors['contact_number'][0]}"
        elif 'vehicle' in errors:
            error_message = f"Vehicle error: {errors['vehicle'][0]}"
        elif 'non_field_errors' in errors:
            error_message = errors['non_field_errors'][0]
            
        return Response(
            {"detail": error_message},
            status=status.HTTP_400_BAD_REQUEST
        )

class SellRequestViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing vehicle sell requests
    """
    serializer_class = SellRequestSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'vehicle__brand', 'vehicle__model']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    permission_classes = [IsAuthenticated, IsOwnerOrStaff]

    def get_queryset(self):
        """
        Return sell requests based on user role
        """
        if self.request.user.is_staff:
            return SellRequest.objects.all()
        return SellRequest.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        """
        Create a new sell request and associate it with the current user
        """
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def submit_for_inspection(self, request, pk=None):
        """
        Submit the sell request for vehicle inspection
        """
        sell_request = self.get_object()
        
        if sell_request.status != SellRequest.Status.DRAFT:
            return Response(
                {'error': 'Only draft sell requests can be submitted for inspection'},
                status=400
            )
        
        if not sell_request.is_document_complete():
            return Response(
                {'error': 'Please complete all required documents before submission'},
                status=400
            )
        
        sell_request.status = SellRequest.Status.PENDING_INSPECTION
        sell_request.save()
        
        # Create an inspection report
        InspectionReport.objects.create(
            sell_request=sell_request,
            status=InspectionReport.Status.SCHEDULED
        )
        
        return Response({'status': 'Submitted for inspection'})

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """
        Cancel a sell request
        """
        sell_request = self.get_object()
        
        if sell_request.status in [
            SellRequest.Status.COMPLETED,
            SellRequest.Status.CANCELLED
        ]:
            return Response(
                {'error': 'Cannot cancel a completed or already cancelled request'},
                status=400
            )
        
        sell_request.status = SellRequest.Status.CANCELLED
        sell_request.save()
        
        return Response({'status': 'Sell request cancelled'})

    @action(detail=True, methods=['get'])
    def timeline(self, request, pk=None):
        """
        Get the timeline of events for a sell request
        """
        sell_request = self.get_object()
        
        timeline = []
        
        # Add creation event
        timeline.append({
            'date': sell_request.created_at,
            'event': 'Sell request created',
            'status': 'completed'
        })
        
        # Add document submission events
        if sell_request.registration_document:
            timeline.append({
                'date': sell_request.registration_document_uploaded_at,
                'event': 'Registration document uploaded',
                'status': 'completed'
            })
        
        if sell_request.insurance_document:
            timeline.append({
                'date': sell_request.insurance_document_uploaded_at,
                'event': 'Insurance document uploaded',
                'status': 'completed'
            })
        
        # Add inspection events
        inspection = sell_request.inspection_report.first()
        if inspection:
            timeline.append({
                'date': inspection.created_at,
                'event': 'Inspection scheduled',
                'status': 'completed' if inspection.completed_at else 'pending'
            })
            
            if inspection.completed_at:
                timeline.append({
                    'date': inspection.completed_at,
                    'event': 'Inspection completed',
                    'status': 'completed'
                })
        
        # Add completion/cancellation event
        if sell_request.status in [SellRequest.Status.COMPLETED, SellRequest.Status.CANCELLED]:
            timeline.append({
                'date': sell_request.updated_at,
                'event': f'Sell request {sell_request.status.lower()}',
                'status': 'completed'
            })
        
        return Response(sorted(timeline, key=lambda x: x['date']))

    @action(detail=True, methods=['get'])
    def status_info(self, request, pk=None):
        """
        Get detailed status information for a sell request
        """
        sell_request = self.get_object()
        
        # Map status to human-readable title and message
        status_info = {
            SellRequest.Status.SUBMITTED: {
                'title': 'Pending Review',
                'message': 'Our team will review your listing shortly.'
            },
            SellRequest.Status.CONFIRMED: {
                'title': 'Confirmed',
                'message': 'Your listing has been confirmed by our team.'
            },
            SellRequest.Status.INSPECTION_SCHEDULED: {
                'title': 'Inspection Scheduled',
                'message': 'We\'ve scheduled an inspection for your vehicle.'
            },
            SellRequest.Status.UNDER_INSPECTION: {
                'title': 'Under Inspection',
                'message': 'Your vehicle is currently being inspected.'
            },
            SellRequest.Status.SERVICE_CENTER: {
                'title': 'At Service Center',
                'message': 'Your vehicle is at our service center.'
            },
            SellRequest.Status.INSPECTION_DONE: {
                'title': 'Inspection Complete',
                'message': 'Your vehicle inspection has been completed.'
            },
            SellRequest.Status.OFFER_MADE: {
                'title': 'Offer Made',
                'message': 'We\'ve made an offer for your vehicle.'
            },
            SellRequest.Status.COUNTER_OFFER: {
                'title': 'Counter Offer',
                'message': 'Your counter offer is under review.'
            },
            SellRequest.Status.DEAL_CLOSED: {
                'title': 'Deal Closed',
                'message': 'The sale has been completed successfully.'
            },
            SellRequest.Status.REJECTED: {
                'title': 'Rejected',
                'message': 'We cannot proceed with your listing at this time.'
            }
        }
        
        # Get the info for the current status
        current_status_info = status_info.get(sell_request.status, {
            'title': f'Status: {sell_request.status}',
            'message': 'Please check back later for updates.'
        })
        
        return Response({
            'status': sell_request.status,
            'status_display': dict(SellRequest.Status.choices).get(sell_request.status, sell_request.status),
            'title': current_status_info['title'],
            'message': current_status_info['message'],
            'updated_at': sell_request.updated_at
        })

class InspectionReportViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing vehicle inspection reports.
    
    Only staff can create/update reports, while owners can view their reports.
    """
    queryset = InspectionReport.objects.all()
    serializer_class = InspectionReportSerializer
    permission_classes = [IsAuthenticated, IsStaffOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = [
        'passed',
        'sell_request__vehicle__vehicle_type',
        'sell_request__status'
    ]
    ordering_fields = ['created_at', 'estimated_repair_cost', 'overall_rating']
    ordering = ['-created_at']

    def get_queryset(self):
        """
        Staff can see all reports, users can only see their own
        """
        if self.request.user.is_staff:
            return self.queryset
        return self.queryset.filter(sell_request__user=self.request.user)

    def perform_create(self, serializer):
        """
        Create a new inspection report and associate it with the current staff user
        """
        if not self.request.user.is_staff:
            raise PermissionDenied("Only staff can create inspection reports")
        serializer.save(inspector=self.request.user)

class PurchaseOfferViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing purchase offers.
    
    Includes functionality for making offers, counter-offers, and accepting/rejecting offers.
    """
    queryset = PurchaseOffer.objects.all()
    serializer_class = PurchaseOfferSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrStaff]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['accepted', 'is_negotiable', 'sell_request__status']
    ordering_fields = ['created_at', 'offer_price', 'valid_until']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return self.queryset
        return self.queryset.filter(
            Q(sell_request__user=user) | 
            Q(created_by=user)
        )

    def perform_create(self, serializer):
        """
        Create a new purchase offer and associate it with the current user
        """
        if not self.request.user.is_staff:
            raise PermissionDenied("Only staff can create purchase offers")
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def counter_offer(self, request, pk=None):
        """Make a counter offer to an existing purchase offer"""
        offer = self.get_object()
        
        if not offer.is_negotiable:
            return Response(
                {"error": "This offer is not negotiable"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        if offer.valid_until and offer.valid_until < timezone.now():
            return Response(
                {"error": "Offer has expired"},
                status=status.HTTP_400_BAD_REQUEST
            )

        counter_price = request.data.get('counter_offer')
        if not counter_price:
            return Response(
                {"error": "counter_offer price is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        offer.counter_offer = counter_price
        offer.save()
        
        return Response(PurchaseOfferSerializer(offer).data)

class VehiclePurchaseViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing vehicle purchases.
    
    Includes functionality for initiating purchases, processing payments,
    and completing vehicle transfers.
    """
    queryset = VehiclePurchase.objects.all()
    serializer_class = VehiclePurchaseSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrStaff]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'payment_method']
    ordering_fields = ['purchase_date', 'completion_date']

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return self.queryset
        return self.queryset.filter(buyer=user)

    @action(detail=True, methods=['post'])
    def process_payment(self, request, pk=None):
        """Process payment for a vehicle purchase"""
        purchase = self.get_object()
        
        if purchase.status != VehiclePurchase.Status.PENDING:
            return Response(
                {"detail": "This purchase is not in pending status"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Here you would integrate with your payment gateway
        # For now, we'll simulate a successful payment
        payment_successful = True
        payment_id = "SIMULATED_PAYMENT_123"

        if payment_successful:
            purchase.payment_id = payment_id
            purchase.status = VehiclePurchase.Status.PROCESSING
            purchase.save()
            return Response({"detail": "Payment processed successfully"})
        
        return Response(
            {"detail": "Payment processing failed"},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=True, methods=['post'])
    def complete_transfer(self, request, pk=None):
        """Complete the vehicle transfer after successful payment"""
        purchase = self.get_object()
        
        if purchase.status != VehiclePurchase.Status.PROCESSING:
            return Response(
                {"detail": "This purchase is not ready for transfer"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if purchase.complete_purchase():
            return Response({"detail": "Vehicle transfer completed successfully"})
        
        return Response(
            {"detail": "Failed to complete vehicle transfer"},
            status=status.HTTP_400_BAD_REQUEST
        )

class VehicleBookingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing vehicle bookings.
    
    Allows users to book vehicles, staff to manage bookings, and
    send notifications about booking status.
    """
    serializer_class = VehicleBookingSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrStaff]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'vehicle__vehicle_type', 'vehicle__brand']
    ordering_fields = ['booking_date']
    ordering = ['-booking_date']
    
    def get_queryset(self):
        """
        Return bookings based on user role:
        - Staff can see all bookings
        - Regular users can only see their own bookings
        """
        if self.request.user.is_staff:
            return VehicleBooking.objects.all()
        return VehicleBooking.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        """Create a new booking and send notification"""
        booking = serializer.save(user=self.request.user)
        
        # Create notification for the user
        Notification.objects.create(
            user=self.request.user,
            type='booking_created',
            title='Vehicle Booking Created',
            message=f'Your booking for {booking.vehicle} has been created and is pending confirmation.',
            data={'booking_id': booking.id, 'vehicle_id': booking.vehicle.id}
        )
        
        # Create notification for staff
        for staff_user in User.objects.filter(is_staff=True):
            Notification.objects.create(
                user=staff_user,
                type='new_booking',
                title='New Vehicle Booking',
                message=f'A new booking has been created for {booking.vehicle} by {booking.user}.',
                data={'booking_id': booking.id, 'vehicle_id': booking.vehicle.id}
            )
    
    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """Confirm a booking"""
        booking = self.get_object()
        
        if booking.status != VehicleBooking.Status.PENDING:
            return Response(
                {"detail": "Only pending bookings can be confirmed"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        booking.confirm_booking()
        return Response(
            {"detail": "Booking confirmed successfully"},
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark a booking as completed"""
        booking = self.get_object()
        
        if booking.status != VehicleBooking.Status.CONFIRMED:
            return Response(
                {"detail": "Only confirmed bookings can be completed"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        booking.complete_booking()
        return Response(
            {"detail": "Booking marked as completed"},
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a booking"""
        booking = self.get_object()
        
        if booking.status in [VehicleBooking.Status.COMPLETED, VehicleBooking.Status.CANCELLED]:
            return Response(
                {"detail": "Cannot cancel a completed or already cancelled booking"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        booking.cancel_booking()
        return Response(
            {"detail": "Booking cancelled successfully"},
            status=status.HTTP_200_OK
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def email_vehicle_summary(request):
    """
    Send a vehicle summary email to the specified recipient
    """
    try:
        data = request.data
        recipient_email = data.get('recipient_email')
        vehicle_id = data.get('vehicle_id')
        summary_data = data.get('summary_data')
        
        if not recipient_email or not vehicle_id or not summary_data:
            return Response({
                'message': 'Missing required fields: recipient_email, vehicle_id, or summary_data'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get vehicle data from the summary_data
        vehicle = summary_data.get('vehicle', {})
        if not vehicle:
            return Response({
                'message': 'Vehicle data is missing from summary data'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create context for email template
        context = {
            'vehicle': vehicle,
            'data': summary_data,
            'user': request.user,
            'recipient_name': data.get('recipient_name', ''),
            'recipient_phone': data.get('recipient_phone', ''),
            'photo_urls': summary_data.get('photo_urls', {}),
        }
        
        # Generate email content with HTML template
        html_content = render_to_string('marketplace/email_templates/vehicle_summary.html', context)
        plain_text = strip_tags(html_content)
        
        # Prepare email subject
        subject = data.get('subject', f"Your Vehicle Listing Summary - {vehicle.get('brand', '')} {vehicle.get('model', '')}")
        
        # Create email message
        email = EmailMultiAlternatives(
            subject=subject,
            body=plain_text,
            from_email=settings.EMAIL_HOST_USER,
            to=[recipient_email],
            reply_to=[settings.DEFAULT_FROM_EMAIL],
        )
        
        # Attach HTML content
        email.attach_alternative(html_content, "text/html")
        
        # Add attachments if requested and available
        if data.get('include_attachments', False) and summary_data.get('photo_urls'):
            # Limit to 3 photos to prevent email size issues
            photo_count = 0
            for key, url in summary_data['photo_urls'].items():
                if photo_count >= 3:
                    break
                    
                # Only attach if it's a base64 image (not an external URL)
                if url and url.startswith('data:image/'):
                    try:
                        # Extract the image data from base64
                        format_type = url.split(';')[0].split('/')[1]
                        img_data = base64.b64decode(url.split(',')[1])
                        
                        # Attach the image
                        email.attach(f"{vehicle.get('brand', 'Vehicle')}_{key}.{format_type}", 
                                    img_data, 
                                    f"image/{format_type}")
                        photo_count += 1
                    except Exception as e:
                        # Log error but continue with other attachments
                        print(f"Error attaching image {key}: {str(e)}")
        
        # Send the email
        email.send()
        
        # Return success response
        return Response({
            'message': 'Vehicle summary email sent successfully',
            'email': recipient_email
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        # Log the error for debugging
        print(f"Error sending vehicle summary email: {str(e)}")
        return Response({
            'message': f'Failed to send vehicle summary email: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)