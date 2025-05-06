from django.db import transaction
from .models import VehicleType, Manufacturer, VehicleModel, UserVehicle
from marketplace.models import Vehicle

class VehicleService:
    @staticmethod
    @transaction.atomic
    def create_user_vehicle(user, vehicle_data):
        """
        Create both UserVehicle and marketplace Vehicle records
        """
        # Create marketplace Vehicle first
        marketplace_vehicle = Vehicle.objects.create(
            owner=user,
            vehicle_type=vehicle_data['vehicle_type'],
            brand=vehicle_data['manufacturer'].name,
            model=vehicle_data['model'].name,
            year=vehicle_data.get('year'),
            registration_number=vehicle_data['registration_number'],
            kms_driven=vehicle_data.get('kms_driven', 0),
            Mileage=vehicle_data.get('mileage', ''),
            fuel_type=vehicle_data.get('fuel_type', Vehicle.FuelType.PETROL),
            engine_capacity=vehicle_data.get('engine_capacity'),
            color=vehicle_data.get('color', 'Not Specified'),
            last_service_date=vehicle_data.get('last_service_date'),
            insurance_valid_till=vehicle_data.get('insurance_valid_till')
        )

        # Create UserVehicle record
        user_vehicle = UserVehicle.objects.create(
            user=user.profile,
            vehicle_type=vehicle_data['vehicle_type'],
            manufacturer=vehicle_data['manufacturer'],
            model=vehicle_data['model'],
            registration_number=vehicle_data['registration_number'],
            purchase_date=vehicle_data.get('purchase_date'),
            vehicle_image=vehicle_data.get('vehicle_image')
        )

        return marketplace_vehicle, user_vehicle

    @staticmethod
    @transaction.atomic
    def update_user_vehicle(user_vehicle, vehicle_data):
        """
        Update both UserVehicle and marketplace Vehicle records
        """
        # Update marketplace Vehicle
        try:
            marketplace_vehicle = Vehicle.objects.get(
                registration_number=user_vehicle.registration_number
            )
            # Handle specific field mapping between UserVehicle and marketplace Vehicle
            if 'mileage' in vehicle_data:
                marketplace_vehicle.Mileage = vehicle_data['mileage']
                
            for key, value in vehicle_data.items():
                if hasattr(marketplace_vehicle, key):
                    setattr(marketplace_vehicle, key, value)
            marketplace_vehicle.save()
        except Vehicle.DoesNotExist:
            pass  # Handle this case based on your business logic

        # Update UserVehicle
        for key, value in vehicle_data.items():
            if hasattr(user_vehicle, key):
                setattr(user_vehicle, key, value)
        user_vehicle.save()

        return marketplace_vehicle, user_vehicle

    @staticmethod
    def get_vehicle_details(registration_number):
        """
        Get combined vehicle details from both models
        """
        try:
            marketplace_vehicle = Vehicle.objects.get(registration_number=registration_number)
            user_vehicle = UserVehicle.objects.get(registration_number=registration_number)
            
            return {
                'marketplace_details': marketplace_vehicle,
                'user_details': user_vehicle,
                'combined': {
                    'registration_number': registration_number,
                    'vehicle_type': user_vehicle.vehicle_type.name,
                    'manufacturer': user_vehicle.manufacturer.name,
                    'model': user_vehicle.model.name,
                    'status': marketplace_vehicle.status,
                    'kms_driven': marketplace_vehicle.kms_driven,
                    'mileage': marketplace_vehicle.Mileage,
                    'last_service_date': marketplace_vehicle.last_service_date,
                    'insurance_valid_till': marketplace_vehicle.insurance_valid_till
                }
            }
        except (Vehicle.DoesNotExist, UserVehicle.DoesNotExist):
            return None 