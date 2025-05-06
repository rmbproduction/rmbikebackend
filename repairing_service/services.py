from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import Q
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import ServiceRequest, FieldStaff, ServiceRequestResponse, LiveLocation, DistancePricingRule
from math import sin, cos, sqrt, atan2, radians
import json

class ServiceRequestManager:
    def __init__(self, service_request):
        self.service_request = service_request
        self.channel_layer = get_channel_layer()

    def find_nearby_mechanics(self, max_distance=5.0):
        """Find available mechanics within the specified radius"""
        customer_location = self.service_request.location
        available_mechanics = FieldStaff.objects.filter(
            is_available=True,
            current_job__isnull=True
        )
        
        nearby_mechanics = [
            mechanic for mechanic in available_mechanics
            if mechanic.is_within_radius(
                customer_location['latitude'],
                customer_location['longitude']
            )
        ]
        return nearby_mechanics

    def calculate_distance(self, lat1, lon1, lat2, lon2):
        """Calculate distance between two points in kilometers"""
        R = 6371  # Earth's radius in kilometers

        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

        dlon = lon2 - lon1
        dlat = lat2 - lat1

        a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        distance = R * c

        return distance

    def calculate_distance_charges(self):
        """Calculate any additional charges based on distance"""
        # Get active pricing rule
        pricing_rule = DistancePricingRule.get_active_rule()
        if not pricing_rule:
            return 0, 0, None  # No charge if no rule is set
        
        # Get customer and service center locations
        customer_lat = self.service_request.location.get('latitude')
        customer_lng = self.service_request.location.get('longitude')
        
        # Use a default service center location or get from settings
        # This should be configured in your application
        service_center_lat = 28.6139  # Example: Delhi coordinates
        service_center_lng = 77.2090  # Change to your actual service center
        
        # Calculate distance
        distance_km = self.calculate_distance(
            customer_lat, customer_lng,
            service_center_lat, service_center_lng
        )
        
        # Check if distance is within the maximum service range
        if distance_km > pricing_rule.max_distance_km:
            return distance_km, 0, {
                "status": "out_of_range",
                "message": f"Location is beyond our service area of {pricing_rule.max_distance_km}km"
            }
        
        # Calculate additional charges
        additional_charges = pricing_rule.calculate_charges(distance_km)
        
        return distance_km, additional_charges, {
            "status": "ok",
            "free_distance_km": pricing_rule.free_distance_km,
            "distance_km": distance_km,
            "additional_charges": float(additional_charges),
            "price_per_km": float(pricing_rule.price_per_km)
        }

    def notify_nearby_mechanics(self):
        """Send notifications to nearby mechanics about new service request"""
        nearby_mechanics = self.find_nearby_mechanics()
        
        if not nearby_mechanics:
            self.service_request.status = 'CANCELLED'
            self.service_request.save()
            self._notify_customer({
                "type": "service.notification",
                "message": "No mechanics available in your area"
            })
            return False

        # Calculate distance-based charges
        distance_km, additional_charges, pricing_info = self.calculate_distance_charges()
        
        # Prepare customer and vehicle information for the notification
        customer = self.service_request.customer
        customer_info = {
            "name": customer.get_full_name(),
            "phone_number": self.service_request.phone_number,
            "address": self.service_request.address,
            "location": self.service_request.location
        }
        
        # Get vehicle details
        vehicle_info = {}
        if self.service_request.vehicle_model:
            vehicle_info["model"] = self.service_request.vehicle_model.name
        if self.service_request.vehicle_manufacturer:
            vehicle_info["manufacturer"] = self.service_request.vehicle_manufacturer.name

        # Notify customer about distance-based pricing
        if pricing_info and additional_charges > 0:
            self._notify_customer({
                "type": "distance_pricing",
                "message": f"Your location is {distance_km:.1f} km away. Additional travel charges of ₹{additional_charges:.2f} will apply.",
                "pricing_details": pricing_info
            })

        for mechanic in nearby_mechanics:
            async_to_sync(self.channel_layer.group_send)(
                f"mechanic_{mechanic.user.id}",
                {
                    "type": "service.request",
                    "message": {
                        "request_id": str(self.service_request.id),
                        "service_type": self.service_request.service_type,
                        "description": self.service_request.description,
                        "customer": customer_info,
                        "vehicle": vehicle_info,
                        "distance": {
                            "kilometers": distance_km,
                            "additional_charges": float(additional_charges)
                        },
                        "created_at": self.service_request.created_at.isoformat()
                    }
                }
            )
        return True

    def handle_mechanic_response(self, mechanic, response, estimated_arrival_time=None):
        """Handle mechanic's response to service request"""
        with transaction.atomic():
            # Create or update response
            service_response, created = ServiceRequestResponse.objects.update_or_create(
                service_request=self.service_request,
                field_staff=mechanic,
                defaults={
                    'response': response,
                    'estimated_arrival_time': estimated_arrival_time
                }
            )

            if response == 'ACCEPT':
                if self.service_request.status == 'PENDING':
                    self.service_request.status = 'ACCEPTED'
                    mechanic.is_available = False
                    mechanic.current_job = self.service_request
                    mechanic.save()
                    self.service_request.save()
                    
                    # Notify customer
                    self._notify_customer({
                        "message": "Mechanic has accepted your request",
                        "mechanic": {
                            "name": mechanic.user.get_full_name(),
                            "rating": mechanic.rating,
                            "estimated_arrival": estimated_arrival_time
                        }
                    })
                    
                    # Notify other mechanics that request is taken
                    self._notify_other_mechanics(mechanic)
                    
                    return True
            return False

    def start_tracking(self, mechanic, latitude, longitude):
        """Start GPS tracking for the mechanic"""
        if self.service_request.status != 'ACCEPTED':
            raise ValidationError("Cannot start tracking - request not accepted")

        LiveLocation.objects.create(
            field_staff=mechanic,
            service_request=self.service_request,
            latitude=latitude,
            longitude=longitude
        )
        
        self.service_request.status = 'IN_PROGRESS'
        self.service_request.save()
        
        self._notify_customer({
            "message": "Mechanic is on the way",
            "location": {
                "latitude": latitude,
                "longitude": longitude
            }
        })

    def update_tracking(self, mechanic, latitude, longitude):
        """Update mechanic's location"""
        if self.service_request.status != 'IN_PROGRESS':
            return

        LiveLocation.objects.create(
            field_staff=mechanic,
            service_request=self.service_request,
            latitude=latitude,
            longitude=longitude
        )
        
        self._notify_customer({
            "type": "location_update",
            "location": {
                "latitude": latitude,
                "longitude": longitude
            }
        })

    def complete_service(self, mechanic, service_cost):
        """Mark service as completed"""
        with transaction.atomic():
            self.service_request.status = 'COMPLETED'
            self.service_request.completion_time = timezone.now()
            self.service_request.service_cost = service_cost
            self.service_request.save()
            
            mechanic.is_available = True
            mechanic.current_job = None
            mechanic.total_jobs += 1
            mechanic.save()
            
            self._notify_customer({
                "message": "Service completed",
                "cost": str(service_cost)
            })

    def _notify_customer(self, message):
        """Send notification to customer"""
        async_to_sync(self.channel_layer.group_send)(
            f"customer_{self.service_request.customer.id}",
            {
                "type": "service.notification",
                "message": message
            }
        )

    def _notify_other_mechanics(self, accepted_mechanic):
        """Notify other mechanics that the request is no longer available"""
        nearby_mechanics = self.find_nearby_mechanics()
        for mechanic in nearby_mechanics:
            if mechanic != accepted_mechanic:
                async_to_sync(self.channel_layer.group_send)(
                    f"mechanic_{mechanic.user.id}",
                    {
                        "type": "service.cancelled",
                        "message": {
                            "request_id": str(self.service_request.id),
                            "reason": "Request accepted by another mechanic"
                        }
                    }
                )