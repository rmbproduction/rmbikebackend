from django.core.management.base import BaseCommand
from spare_parts.models import PartCategory, SparePart
from vehicle.models import Manufacturer, VehicleModel, VehicleType
from django.core.files.base import ContentFile
from decimal import Decimal
import json

class Command(BaseCommand):
    help = 'Sets up sample spare parts data'

    def handle(self, *args, **options):
        self.stdout.write('Setting up spare parts data...')

        # Create part categories
        self.create_categories()

        # Create sample spare parts
        self.create_spare_parts()

        self.stdout.write(self.style.SUCCESS('Successfully set up spare parts data'))

    def create_categories(self):
        categories = [
            {
                'name': 'Engine Parts',
                'description': 'Parts related to the engine system',
                'subcategories': [
                    {'name': 'Pistons', 'description': 'Engine pistons and related components'},
                    {'name': 'Valves', 'description': 'Engine valves and valve train components'},
                    {'name': 'Gaskets', 'description': 'Engine sealing and gasket components'},
                ]
            },
            {
                'name': 'Brake System',
                'description': 'Parts related to the braking system',
                'subcategories': [
                    {'name': 'Brake Pads', 'description': 'Friction components for braking'},
                    {'name': 'Brake Discs', 'description': 'Brake rotors and discs'},
                    {'name': 'Brake Calipers', 'description': 'Hydraulic brake calipers'},
                ]
            },
            {
                'name': 'Transmission',
                'description': 'Parts related to power transmission',
                'subcategories': [
                    {'name': 'Chains', 'description': 'Drive chains and sprockets'},
                    {'name': 'Clutch', 'description': 'Clutch plates and components'},
                    {'name': 'Gears', 'description': 'Transmission gears and shafts'},
                ]
            },
        ]

        for category_data in categories:
            category, _ = PartCategory.objects.get_or_create(
                name=category_data['name'],
                defaults={
                    'description': category_data['description']
                }
            )

            for sub_data in category_data['subcategories']:
                PartCategory.objects.get_or_create(
                    name=sub_data['name'],
                    defaults={
                        'description': sub_data['description'],
                        'parent': category
                    }
                )

    def create_spare_parts(self):
        # Get some sample data
        manufacturers = Manufacturer.objects.all()
        vehicle_types = VehicleType.objects.all()
        categories = PartCategory.objects.all()

        sample_parts = [
            {
                'name': 'High Performance Brake Pad Set',
                'category_name': 'Brake Pads',
                'part_number': 'BP-2023-HP',
                'description': 'High-performance brake pads designed for optimal stopping power and durability.',
                'features': '- Premium friction material\n- Extended lifespan\n- Reduced brake dust\n- Quiet operation',
                'specifications': {
                    'material': 'Semi-metallic compound',
                    'position': 'Front',
                    'thickness': '10mm',
                    'weight': '0.5kg'
                },
                'price': '1299.99',
                'stock_quantity': 50
            },
            {
                'name': 'Premium Engine Piston Kit',
                'category_name': 'Pistons',
                'part_number': 'EP-2023-PRO',
                'description': 'Professional grade engine piston kit for enhanced performance and reliability.',
                'features': '- Forged aluminum construction\n- High compression ratio\n- Includes piston rings\n- OEM quality',
                'specifications': {
                    'material': 'Forged aluminum',
                    'diameter': '54mm',
                    'compression_ratio': '11:1',
                    'weight': '0.3kg'
                },
                'price': '2499.99',
                'stock_quantity': 30
            },
            {
                'name': 'Heavy Duty Drive Chain',
                'category_name': 'Chains',
                'part_number': 'CH-2023-HD',
                'description': 'Heavy-duty drive chain for superior power transmission and longevity.',
                'features': '- X-ring design\n- High tensile strength\n- Corrosion resistant\n- Pre-stretched',
                'specifications': {
                    'type': 'X-ring chain',
                    'pitch': '520',
                    'length': '120 links',
                    'weight': '1.2kg'
                },
                'price': '1899.99',
                'stock_quantity': 40
            }
        ]

        for part_data in sample_parts:
            # Get category
            category = PartCategory.objects.get(name=part_data['category_name'])
            
            # Create spare part
            spare_part, created = SparePart.objects.get_or_create(
                part_number=part_data['part_number'],
                defaults={
                    'name': part_data['name'],
                    'category': category,
                    'description': part_data['description'],
                    'features': part_data['features'],
                    'specifications': part_data['specifications'],
                    'price': Decimal(part_data['price']),
                    'stock_quantity': part_data['stock_quantity'],
                    'availability_status': 'in_stock'
                }
            )

            if created:
                # Add compatibility with all manufacturers and vehicle types
                spare_part.manufacturers.set(manufacturers)
                spare_part.vehicle_types.set(vehicle_types)
                
                # Add compatibility with some vehicle models (first 3 from each manufacturer)
                for manufacturer in manufacturers:
                    models = VehicleModel.objects.filter(manufacturer=manufacturer)[:3]
                    spare_part.vehicle_models.add(*models)

                self.stdout.write(f'Created spare part: {spare_part.name}') 