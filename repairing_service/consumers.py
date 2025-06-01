import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import FieldStaff, ServiceRequest, LiveLocation
from django.utils import timezone

User = get_user_model()

class ServiceRequestConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        if not self.user.is_authenticated:
            await self.close()
            return

        # Join appropriate group based on user type
        if self.user.email.endswith('@field.repairmybike.in'):
            self.group_name = f"mechanic_{self.user.id}"
        else:
            self.group_name = f"customer_{self.user.id}"

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')

        if message_type == 'location_update' and self.user.email.endswith('@field.repairmybike.in'):
            await self.handle_location_update(data)
        elif message_type == 'service_response':
            await self.handle_service_response(data)
        elif message_type == 'start_tracking':
            await self.handle_start_tracking(data)
        elif message_type == 'complete_service':
            await self.handle_complete_service(data)

    async def handle_location_update(self, data):
        if not await self.is_valid_field_staff():
            return

        # Save location to database
        await self.save_location_update(data)

        # Send location update to customer
        await self.channel_layer.group_send(
            f"customer_{data['customer_id']}",
            {
                'type': 'location_update',
                'message': {
                    'latitude': data['latitude'],
                    'longitude': data['longitude'],
                    'mechanic_id': self.user.id,
                    'timestamp': timezone.now().isoformat()
                }
            }
        )

        # Also notify admin if needed
        if data.get('notify_admin', False):
            await self.channel_layer.group_send(
                "admin_tracking",
                {
                    'type': 'location_update',
                    'message': {
                        'latitude': data['latitude'],
                        'longitude': data['longitude'],
                        'mechanic_id': self.user.id,
                        'customer_id': data['customer_id'],
                        'service_request_id': data['service_request_id'],
                        'timestamp': timezone.now().isoformat()
                    }
                }
            )

    async def handle_service_response(self, data):
        if not await self.is_valid_field_staff():
            return

        # Update response in database
        success = await self.save_service_response(data)
        if not success:
            return

        # Notify customer
        await self.channel_layer.group_send(
            f"customer_{data['customer_id']}",
            {
                'type': 'service_notification',
                'message': {
                    'type': 'response',
                    'mechanic_name': self.user.get_full_name(),
                    'response': data['response'],
                    'estimated_arrival': data.get('estimated_arrival_time'),
                    'service_request_id': data['service_request_id']
                }
            }
        )

    async def handle_start_tracking(self, data):
        if not await self.is_valid_field_staff():
            return

        # Start service in database
        success = await self.start_service_tracking(data)
        if not success:
            return

        # Notify customer that tracking has started
        await self.channel_layer.group_send(
            f"customer_{data['customer_id']}",
            {
                'type': 'service_notification',
                'message': {
                    'type': 'tracking_started',
                    'mechanic_name': self.user.get_full_name(),
                    'initial_location': {
                        'latitude': data['latitude'],
                        'longitude': data['longitude']
                    },
                    'service_request_id': data['service_request_id']
                }
            }
        )

    async def handle_complete_service(self, data):
        if not await self.is_valid_field_staff():
            return

        # Complete service in database
        success = await self.complete_service(data)
        if not success:
            return

        # Notify customer
        await self.channel_layer.group_send(
            f"customer_{data['customer_id']}",
            {
                'type': 'service_notification',
                'message': {
                    'type': 'service_completed',
                    'service_cost': data['service_cost'],
                    'completion_time': timezone.now().isoformat(),
                    'service_request_id': data['service_request_id']
                }
            }
        )

    async def service_notification(self, event):
        await self.send(text_data=json.dumps(event['message']))

    async def service_request(self, event):
        """Handle incoming service requests for mechanics"""
        await self.send(text_data=json.dumps({
            'type': 'new_service_request',
            'data': event['message']
        }))

    async def service_cancelled(self, event):
        """Handle service cancellation notifications"""
        await self.send(text_data=json.dumps({
            'type': 'service_cancelled',
            'data': event['message']
        }))

    async def location_update(self, event):
        await self.send(text_data=json.dumps(event['message']))

    @database_sync_to_async
    def is_valid_field_staff(self):
        return (
            self.user.email.endswith('@field.repairmybike.in') and
            FieldStaff.objects.filter(user=self.user).exists()
        )

    @database_sync_to_async
    def save_location_update(self, data):
        try:
            field_staff = FieldStaff.objects.get(user=self.user)
            service_request = ServiceRequest.objects.get(id=data['service_request_id'])
            
            # Save to LiveLocation model
            LiveLocation.objects.create(
                field_staff=field_staff,
                service_request=service_request,
                latitude=data['latitude'],
                longitude=data['longitude']
            )
            
            # Update field staff current location
            field_staff.update_location(data['latitude'], data['longitude'])
            return True
        except Exception:
            return False

    @database_sync_to_async
    def save_service_response(self, data):
        from .services import ServiceRequestManager
        try:
            field_staff = FieldStaff.objects.get(user=self.user)
            service_request = ServiceRequest.objects.get(id=data['service_request_id'])
            
            manager = ServiceRequestManager(service_request)
            return manager.handle_mechanic_response(
                field_staff, 
                data['response'], 
                data.get('estimated_arrival_time')
            )
        except Exception:
            return False

    @database_sync_to_async
    def start_service_tracking(self, data):
        from .services import ServiceRequestManager
        try:
            field_staff = FieldStaff.objects.get(user=self.user)
            service_request = ServiceRequest.objects.get(id=data['service_request_id'])
            
            manager = ServiceRequestManager(service_request)
            manager.start_tracking(
                field_staff, 
                data['latitude'], 
                data['longitude']
            )
            return True
        except Exception:
            return False

    @database_sync_to_async
    def complete_service(self, data):
        from .services import ServiceRequestManager
        try:
            field_staff = FieldStaff.objects.get(user=self.user)
            service_request = ServiceRequest.objects.get(id=data['service_request_id'])
            
            manager = ServiceRequestManager(service_request)
            manager.complete_service(field_staff, data['service_cost'])
            return True
        except Exception:
            return False

class AdminDashboardConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for the admin dashboard"""
    
    async def connect(self):
        self.user = self.scope["user"]
        
        # Verify that the user is authenticated and is an admin
        if not self.user.is_authenticated:
            await self.close()
            return
            
        if not self.user.is_staff and not self.user.is_superuser:
            await self.close()
            return
        
        # Add the user to the admin group
        self.group_name = "admin_dashboard"
        
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        # Also add to admin tracking group for location updates
        await self.channel_layer.group_add(
            "admin_tracking",
            self.channel_name
        )
        
        await self.accept()
        
        # Send initial data
        await self.send_initial_data()
    
    async def disconnect(self, close_code):
        # Remove from groups
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
        
        await self.channel_layer.group_discard(
            "admin_tracking",
            self.channel_name
        )
    
    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')
        
        if message_type == 'refresh':
            # Send latest data if admin requests a refresh
            await self.send_initial_data()
        elif message_type == 'mark_notification_read':
            # Mark a notification as read
            notification_id = data.get('notification_id')
            if notification_id:
                success = await self.mark_notification_read(notification_id)
                await self.send(text_data=json.dumps({
                    'type': 'notification_marked_read',
                    'notification_id': notification_id,
                    'success': success
                }))
        elif message_type == 'update_request_status':
            # Update a request status
            request_id = data.get('request_id')
            new_status = data.get('status')
            if request_id and new_status:
                success, request_data = await self.update_request_status(request_id, new_status)
                await self.send(text_data=json.dumps({
                    'type': 'request_status_updated',
                    'request_id': request_id,
                    'success': success,
                    'request': request_data if success else None
                }))
                
                # If successful, also broadcast the update to other admins
                if success:
                    await self.channel_layer.group_send(
                        self.group_name,
                        {
                            'type': 'request_update',
                            'message': {
                                'request_id': request_id,
                                'status': new_status,
                                'request': request_data
                            }
                        }
                    )
    
    async def send_initial_data(self):
        """Send initial data to the admin dashboard"""
        statistics = await self.get_statistics()
        notifications = await self.get_notifications()
        requests = await self.get_requests()
        
        await self.send(text_data=json.dumps({
            'type': 'initial_data',
            'statistics': statistics,
            'notifications': notifications,
            'requests': requests
        }))
    
    async def notification_update(self, event):
        """Handle new notification events"""
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'notification': event['message']
        }))
    
    async def request_update(self, event):
        """Handle request update events"""
        await self.send(text_data=json.dumps({
            'type': 'request',
            'request': event['message']
        }))
    
    async def statistics_update(self, event):
        """Handle statistics update events"""
        await self.send(text_data=json.dumps({
            'type': 'statistics_update',
            'statistics': event['message']
        }))
    
    async def location_update(self, event):
        """Handle location update events from field staff"""
        await self.send(text_data=json.dumps({
            'type': 'location_update',
            'location': event['message']
        }))
    
    @database_sync_to_async
    def get_statistics(self):
        """Get dashboard statistics data"""
        from django.db.models import Sum, Count
        from marketplace.models import Vehicle, SellRequest
        from accounts.models import User, UserProfile
        
        # These queries would be optimized in production
        total_users = User.objects.count()
        total_vehicles = Vehicle.objects.count()
        total_sell_requests = SellRequest.objects.count()
        total_service_requests = ServiceRequest.objects.count()
        pending_sell_requests = SellRequest.objects.filter(status='PENDING').count()
        pending_repair_requests = ServiceRequest.objects.filter(status='PENDING').count()
        
        # Calculate revenue (this is a simplified example)
        from marketplace.models import VehiclePurchase
        vehicle_revenue = VehiclePurchase.objects.aggregate(total=Sum('price'))['total'] or 0
        service_revenue = ServiceRequest.objects.filter(status='COMPLETED').aggregate(total=Sum('total_amount'))['total'] or 0
        total_revenue = vehicle_revenue + service_revenue
        
        return {
            'totalUsers': total_users,
            'totalVehicles': total_vehicles,
            'totalSales': total_sell_requests,
            'totalServices': total_service_requests,
            'pendingSellRequests': pending_sell_requests,
            'pendingRepairRequests': pending_repair_requests,
            'totalRevenue': f'₹{total_revenue:,.2f}'
        }
    
    @database_sync_to_async
    def get_notifications(self):
        """Get latest notifications for admin dashboard"""
        from marketplace.models import Notification
        
        # Get latest 50 notifications
        notifications = Notification.objects.order_by('-created_at')[:50]
        
        return [
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
    
    @database_sync_to_async
    def get_requests(self):
        """Get latest requests for admin dashboard"""
        from marketplace.models import SellRequest
        
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
        
        return all_requests[:50]  # Return the most recent 50 requests
    
    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        """Mark a notification as read"""
        from marketplace.models import Notification
        try:
            notification = Notification.objects.get(id=notification_id)
            notification.is_read = True
            notification.save()
            return True
        except Exception as e:
            print(f"Error marking notification as read: {e}")
            return False
    
    @database_sync_to_async
    def update_request_status(self, request_id, new_status):
        """Update a request status"""
        # This is a simplified implementation
        # In a real application, you would handle different request types
        try:
            # Try to find a sell request first
            from marketplace.models import SellRequest
            sell_request = SellRequest.objects.filter(id=request_id).first()
            
            if sell_request:
                old_status = sell_request.status
                sell_request.status = new_status
                sell_request.save()
                
                # Return updated data
                return True, {
                    'id': str(sell_request.id),
                    'type': 'sell_request',
                    'status': sell_request.status,
                    'old_status': old_status,
                    'updated_at': timezone.now().isoformat()
                }
            
            # If not a sell request, try service request
            service_request = ServiceRequest.objects.filter(id=request_id).first()
            
            if service_request:
                old_status = service_request.status
                service_request.status = new_status
                service_request.save()
                
                # Return updated data
                return True, {
                    'id': str(service_request.id),
                    'type': 'service_request',
                    'status': service_request.status,
                    'old_status': old_status,
                    'updated_at': timezone.now().isoformat()
                }
            
            return False, None
        except Exception as e:
            print(f"Error updating request status: {e}")
            return False, None

def get_stats():
    """Get current statistics"""
    total_users = get_user_model().objects.count()