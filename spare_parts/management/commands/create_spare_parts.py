from django.core.management.base import BaseCommand
from spare_parts.models import PartCategory, SparePart
from django.utils.text import slugify
from decimal import Decimal
import random

class Command(BaseCommand):
    help = 'Create sample spare parts in the database'

    def handle(self, *args, **options):
        # First, let's create some categories if they don't exist
        categories = {
            'engine_parts': 'Engine Parts',
            'body_parts': 'Body Parts',
            'lighting': 'Lighting',
            'electrical': 'Electrical',
            'brakes': 'Brakes',
            'suspension': 'Suspension',
            'accessories': 'Accessories'
        }
        
        created_categories = {}
        for slug, name in categories.items():
            category, created = PartCategory.objects.get_or_create(
                slug=slug,
                defaults={
                    'name': name,
                    'description': f'All {name.lower()} for your bike'
                }
            )
            created_categories[slug] = category
            status = 'Created' if created else 'Already exists'
            self.stdout.write(self.style.SUCCESS(f'{status}: Category {name}'))
            
        # Now create the spare parts
        spare_parts = [
            {
                'name': 'Battery',
                'category': created_categories['electrical'],
                'description': 'High-quality battery for your bike with long life and reliable performance.',
                'features': 'Maintenance-free\nLong life cycle\nVibration resistant\nQuick charging',
                'part_number': 'BAT001',
                'price': Decimal('1499.00'),
                'stock_quantity': random.randint(5, 20),
            },
            {
                'name': 'Visor / Windshield',
                'category': created_categories['body_parts'],
                'description': 'Premium windshield that protects from wind and debris while providing clear visibility.',
                'features': 'UV resistant\nShatter-proof\nAerodynamic design\nEasy installation',
                'part_number': 'VIS001',
                'price': Decimal('899.00'),
                'stock_quantity': random.randint(5, 20),
            },
            {
                'name': 'Mudguard / Midguard',
                'category': created_categories['body_parts'],
                'description': 'Durable mudguard that prevents splashing and protects your bike from dirt and mud.',
                'features': 'Weather resistant\nLightweight\nFlexible yet durable\nEasy to install',
                'part_number': 'MUD001',
                'price': Decimal('649.00'),
                'stock_quantity': random.randint(5, 20),
            },
            {
                'name': 'Half Engine',
                'category': created_categories['engine_parts'],
                'description': 'Reliable half engine assembly for quick replacement and repair.',
                'features': 'OEM quality\nHigh performance\nTested for durability\nCompatible with multiple bike models',
                'part_number': 'ENG001',
                'price': Decimal('8999.00'),
                'stock_quantity': random.randint(2, 10),
            },
            {
                'name': 'Full Engine',
                'category': created_categories['engine_parts'],
                'description': 'Complete engine assembly built to OEM specifications for maximum performance.',
                'features': 'Factory tested\nComplete with all components\nOptimized for performance\nOne year warranty',
                'part_number': 'ENG002',
                'price': Decimal('15999.00'),
                'stock_quantity': random.randint(1, 5),
            },
            {
                'name': 'Headlight',
                'category': created_categories['lighting'],
                'description': 'Bright and energy-efficient headlight for better visibility at night.',
                'features': 'LED technology\nLow power consumption\nLong life span\nWaterproof design',
                'part_number': 'LGT001',
                'price': Decimal('1299.00'),
                'stock_quantity': random.randint(5, 20),
            },
            {
                'name': 'Indicator',
                'category': created_categories['lighting'],
                'description': 'Clear and bright indicators that ensure your signals are visible to other road users.',
                'features': 'Bright LED lights\nDurable construction\nWaterproof\nEasy installation',
                'part_number': 'LGT002',
                'price': Decimal('499.00'),
                'stock_quantity': random.randint(10, 30),
            },
            {
                'name': 'Rear View Mirrors',
                'category': created_categories['accessories'],
                'description': 'Wide-angle rear view mirrors that provide excellent visibility behind you.',
                'features': 'Adjustable position\nVibration resistant\nWeather resistant\nWide viewing angle',
                'part_number': 'MIR001',
                'price': Decimal('699.00'),
                'stock_quantity': random.randint(5, 20),
            },
            {
                'name': 'Side Stand',
                'category': created_categories['accessories'],
                'description': 'Sturdy side stand for safely parking your bike on various surfaces.',
                'features': 'Heavy-duty construction\nNon-slip foot\nDurable spring mechanism\nEasy to deploy and retract',
                'part_number': 'STD001',
                'price': Decimal('399.00'),
                'stock_quantity': random.randint(5, 20),
            },
            {
                'name': 'Main Stand',
                'category': created_categories['accessories'],
                'description': 'Strong and stable main stand for secure parking and maintenance work.',
                'features': 'Heavy-duty steel construction\nDurable spring mechanism\nRust-resistant coating\nStable on various surfaces',
                'part_number': 'STD002',
                'price': Decimal('899.00'),
                'stock_quantity': random.randint(5, 15),
            },
            {
                'name': 'Number Plate Holder',
                'category': created_categories['body_parts'],
                'description': 'Stylish and legal number plate holder that securely displays your registration.',
                'features': 'Weather resistant\nRust-proof material\nSecurely holds standard plates\nComplies with regulations',
                'part_number': 'NPH001',
                'price': Decimal('299.00'),
                'stock_quantity': random.randint(10, 20),
            },
            {
                'name': 'Spark Plug',
                'category': created_categories['engine_parts'],
                'description': 'High-performance spark plug for efficient combustion and better fuel economy.',
                'features': 'Efficient ignition\nImproved fuel economy\nReduced emissions\nLong service life',
                'part_number': 'SPK001',
                'price': Decimal('199.00'),
                'stock_quantity': random.randint(20, 50),
            },
            {
                'name': 'Horn',
                'category': created_categories['electrical'],
                'description': 'Loud and clear horn that ensures you\'re heard in traffic.',
                'features': 'Loud and clear sound\nWeather resistant\nLong-lasting performance\nEasy installation',
                'part_number': 'HRN001',
                'price': Decimal('349.00'),
                'stock_quantity': random.randint(10, 30),
            },
            {
                'name': 'Brake Shoe',
                'category': created_categories['brakes'],
                'description': 'High-quality brake shoes for reliable stopping power in all conditions.',
                'features': 'Superior stopping power\nHeat resistant\nLow noise operation\nLong service life',
                'part_number': 'BRK001',
                'price': Decimal('399.00'),
                'stock_quantity': random.randint(15, 40),
            },
            {
                'name': 'Air Filter',
                'category': created_categories['engine_parts'],
                'description': 'High-flow air filter that improves engine performance while blocking contaminants.',
                'features': 'High filtration efficiency\nImproved airflow\nEnhances engine performance\nWashable and reusable',
                'part_number': 'FLT001',
                'price': Decimal('349.00'),
                'stock_quantity': random.randint(10, 30),
            },
        ]
        
        # Add the parts to the database
        for part_data in spare_parts:
            name = part_data['name']
            slug = slugify(name)
            
            # Check if part already exists
            if SparePart.objects.filter(slug=slug).exists():
                self.stdout.write(self.style.WARNING(f'Already exists: {name}'))
                continue
                
            # Create the part
            part = SparePart.objects.create(
                name=name,
                slug=slug,
                part_number=part_data['part_number'],
                category=part_data['category'],
                description=part_data['description'],
                features=part_data['features'],
                price=part_data['price'],
                stock_quantity=part_data['stock_quantity'],
                availability_status='in_stock' if part_data['stock_quantity'] > 0 else 'out_of_stock',
                specifications={
                    'weight': f'{random.randint(1, 10)} kg',
                    'dimensions': f'{random.randint(10, 50)}x{random.randint(10, 50)}x{random.randint(5, 20)} cm',
                    'material': random.choice(['Aluminum', 'Steel', 'Plastic', 'Rubber', 'Carbon Fiber']),
                    'warranty': f'{random.randint(6, 24)} months'
                },
                meta_title=name,
                meta_description=part_data['description'][:150],
                is_featured=random.choice([True, False]),
                is_active=True
            )
            
            self.stdout.write(self.style.SUCCESS(f'Created: {name}'))
            
        self.stdout.write(self.style.SUCCESS('Spare parts creation completed!')) 