from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.db.models import Sum, Count
from django.utils import timezone
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json
import uuid

from marketplace.models import Vehicle, SellRequest, Notification, VehiclePurchase
from accounts.models import User, UserProfile
from repairing_service.models import ServiceRequest

class AdminDashboardStatisticsView(APIView):
    """
    API endpoint for admin dashboard statistics
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get(self, request):
        """Get dashboard statistics data"""
        try:
            # Get user counts
            total_users = User.objects.count()
            total_vehicles = Vehicle.objects.count()
            total_sell_requests = SellRequest.objects.count()
            total_service_requests = ServiceRequest.objects.count()
            pending_sell_requests = SellRequest.objects.filter(status='PENDING').count()
            pending_repair_requests = ServiceRequest.objects.filter(status='PENDING').count()
            
            # Calculate revenue (this is a simplified example)
            vehicle_revenue = VehiclePurchase.objects.aggregate(total=Sum('price'))['total'] or 0
            service_revenue = ServiceRequest.objects.filter(status='COMPLETED').aggregate(total=Sum('total_amount'))['total'] or 0
            total_revenue = vehicle_revenue + service_revenue
            
            statistics = {
                'totalUsers': total_users,
                'totalVehicles': total_vehicles,
                'totalSales': total_sell_requests,
                'totalServices': total_service_requests,
                'pendingSellRequests': pending_sell_requests,
                'pendingRepairRequests': pending_repair_requests,
                'totalRevenue': f'₹{total_revenue:,.2f}'
            }
            
            return Response(statistics)
        
        except Exception as e:
            return Response(
                {'error': f'Error retrieving dashboard statistics: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AdminNotificationsView(APIView):
    """
    API endpoint for admin notifications
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get(self, request):
        """Get latest notifications for admin dashboard"""
        try:
            # Get notifications
            notifications = Notification.objects.order_by('-created_at')[:50]
            
            notification_data = [
                {
                    'id': str(notification.id),
                    'type': notification.type,
                    'title': notification.title,
                    'message': notification.message,
                    'created_at': notification.created_at.isoformat(),
                    'is_read': notification.is_read,
                    'data': notification.data
                }
                for notification in notifications
            ]
            
            return Response(notification_data)
        
        except Exception as e:
            return Response(
                {'error': f'Error retrieving notifications: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def patch(self, request, notification_id=None):
        """Mark a notification as read"""
        try:
            if not notification_id and request.data.get('notification_id'):
                notification_id = request.data.get('notification_id')
                
            if not notification_id:
                return Response(
                    {'error': 'Notification ID is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            notification = Notification.objects.get(id=notification_id)
            notification.is_read = True
            notification.save()
            
            return Response({'success': True})
        
        except Notification.DoesNotExist:
            return Response(
                {'error': 'Notification not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Error marking notification as read: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AdminRequestsView(APIView):
    """
    API endpoint for admin to view all requests
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get(self, request):
        """Get latest requests for admin dashboard"""
        try:
            # Get sell requests
            sell_requests = SellRequest.objects.select_related('user', 'vehicle').order_by('-created_at')[:25]
            sell_request_data = [
                {
                    'id': str(req.id),
                    'type': 'sell_request',
                    'status': req.status,
                    'created_at': req.created_at.isoformat(),
                    'customer_name': req.user.get_full_name() or req.user.email,
                    'vehicle_details': f"{req.vehicle.brand} {req.vehicle.model} ({req.vehicle.year})" if req.vehicle else "Unknown Vehicle",
                    'price': f"₹{req.vehicle.expected_price:,.2f}" if req.vehicle and req.vehicle.expected_price else None,
                    'details': {
                        'pickup_address': req.pickup_address,
                        'contact_number': req.contact_number,
                        'documents_uploaded': req.registration_certificate and req.insurance_document,
                    }
                }
                for req in sell_requests
            ]
            
            # Get service requests
            service_requests = ServiceRequest.objects.order_by('-created_at')[:25]
            service_request_data = [
                {
                    'id': str(req.id),
                    'type': 'service_request',
                    'status': req.status,
                    'created_at': req.created_at.isoformat(),
                    'customer_name': req.customer_name,
                    'vehicle_details': f"{req.vehicle_type} - {req.manufacturer} {req.vehicle_model}" if req.vehicle_type else "Unknown Vehicle",
                    'price': f"₹{req.total_amount:,.2f}" if req.total_amount else None,
                    'details': {
                        'address': req.address,
                        'city': req.city,
                        'state': req.state,
                        'scheduled_date': req.scheduled_date.isoformat() if req.scheduled_date else None,
                        'schedule_time': req.schedule_time,
                    }
                }
                for req in service_requests
            ]
            
            # Get vehicle bookings (would be implemented in a real application)
            vehicle_bookings = []
            
            # Combine all requests and sort by created date
            all_requests = sell_request_data + service_request_data + vehicle_bookings
            all_requests.sort(key=lambda x: x['created_at'], reverse=True)
            
            return Response(all_requests[:50])  # Return the most recent 50 requests
        
        except Exception as e:
            return Response(
                {'error': f'Error retrieving requests: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AdminRequestStatusUpdateView(APIView):
    """
    API endpoint for admin to update request status
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def patch(self, request, request_id):
        """Update a request status"""
        try:
            new_status = request.data.get('status')
            if not new_status:
                return Response(
                    {'error': 'Status is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Try to update sell request
            try:
                sell_request = SellRequest.objects.get(id=request_id)
                old_status = sell_request.status
                sell_request.status = new_status
                sell_request.save()
                
                # Create a notification for the user
                Notification.objects.create(
                    user=sell_request.user,
                    type='status_change',
                    title='Sell Request Status Updated',
                    message=f'Your sell request status has been updated to {new_status}.',
                    data={
                        'sell_request_id': str(sell_request.id),
                        'old_status': old_status,
                        'new_status': new_status
                    }
                )
                
                # Broadcast the update to connected admin clients
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    'admin_dashboard',
                    {
                        'type': 'request_update',
                        'message': {
                            'id': str(sell_request.id),
                            'type': 'sell_request',
                            'status': sell_request.status,
                            'old_status': old_status,
                            'updated_at': timezone.now().isoformat()
                        }
                    }
                )
                
                return Response({
                    'id': str(sell_request.id),
                    'type': 'sell_request',
                    'status': sell_request.status,
                    'old_status': old_status,
                    'updated_at': timezone.now().isoformat()
                })
            except SellRequest.DoesNotExist:
                pass
            
            # Try to update service request
            try:
                service_request = ServiceRequest.objects.get(id=request_id)
                old_status = service_request.status
                service_request.status = new_status
                service_request.save()
                
                # Create a notification for the user if available
                if service_request.user:
                    Notification.objects.create(
                        user=service_request.user,
                        type='service_status_change',
                        title='Service Request Status Updated',
                        message=f'Your service request status has been updated to {new_status}.',
                        data={
                            'service_request_id': str(service_request.id),
                            'old_status': old_status,
                            'new_status': new_status
                        }
                    )
                
                # Broadcast the update to connected admin clients
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    'admin_dashboard',
                    {
                        'type': 'request_update',
                        'message': {
                            'id': str(service_request.id),
                            'type': 'service_request',
                            'status': service_request.status,
                            'old_status': old_status,
                            'updated_at': timezone.now().isoformat()
                        }
                    }
                )
                
                return Response({
                    'id': str(service_request.id),
                    'type': 'service_request',
                    'status': service_request.status,
                    'old_status': old_status,
                    'updated_at': timezone.now().isoformat()
                })
            except ServiceRequest.DoesNotExist:
                pass
            
            # If neither request type found, return error
            return Response(
                {'error': 'Request not found'},
                status=status.HTTP_404_NOT_FOUND
            )
            
        except Exception as e:
            return Response(
                {'error': f'Error updating request status: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            ) 