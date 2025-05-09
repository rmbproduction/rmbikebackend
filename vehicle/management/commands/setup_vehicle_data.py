from django.core.management.base import BaseCommand
from vehicle.models import Manufacturer, VehicleType, VehicleModel

class Command(BaseCommand):
    help = 'Sets up proper vehicle data including manufacturers and their models'

    def handle(self, *args, **options):
        self.stdout.write('Setting up vehicle data...')

        # Create or update vehicle types
        bike_type, _ = VehicleType.objects.get_or_create(
            name='Bike',
            defaults={'name': 'Bike'}
        )
        scooter_type, _ = VehicleType.objects.get_or_create(
            name='Scooter',
            defaults={'name': 'Scooter'}
        )

        # Create or update manufacturers
        honda, _ = Manufacturer.objects.get_or_create(
            name='Honda',
            defaults={'name': 'Honda'}
        )
        hero, _ = Manufacturer.objects.get_or_create(
            name='Hero',
            defaults={'name': 'Hero'}
        )

        # Define proper vehicle models for each manufacturer
        honda_models = {
            'Bike': [
                'CB Shine',
                'CB Unicorn',
                'CB Hornet',
                'CB300R',
                'CB350',
            ,
                'discover'],
            'Scooter': [
                'Activa 6G',
                'Dio',
                'Grazia',
                'Aviator',
            ]
        }

        hero_models = {
            'Bike': [
                'Splendor Plus',
                'HF Deluxe',
                'Glamour',
                'Xtreme 160R',
                'Xpulse 200'
            ],
            'Scooter': [
                'Maestro Edge',
                'Pleasure Plus',
                'Destini 125',
            ]
        }

        # Function to create vehicle models
        def create_vehicle_models(manufacturer, models_dict):
            # First, get all existing models for this manufacturer
            existing_models = VehicleModel.objects.filter(manufacturer=manufacturer)
            
            # Create a set of tuples (name, vehicle_type_name) for easy comparison
            existing_model_set = {(model.name, model.vehicle_type.name) for model in existing_models}
            
            # Create new models
            for vehicle_type_name, model_names in models_dict.items():
                vehicle_type = VehicleType.objects.get(name=vehicle_type_name)
                for model_name in model_names:
                    if (model_name, vehicle_type_name) not in existing_model_set:
                        VehicleModel.objects.create(
                            name=model_name,
                            manufacturer=manufacturer,
                            vehicle_type=vehicle_type
                        )
                        self.stdout.write(f'Created {manufacturer.name} {model_name} ({vehicle_type_name})')

        # Create vehicle models for each manufacturer
        create_vehicle_models(honda, honda_models)
        create_vehicle_models(hero, hero_models)

        self.stdout.write(self.style.SUCCESS('Vehicle data setup completed successfully!')) 