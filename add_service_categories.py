import os
import django
import decimal

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'authback.settings')
django.setup()

from repairing_service.models import ServiceCategory, Service

# Service categories and their services with price ranges
service_data = [
    {
        "category": "Engine-Related Repairs",
        "description": "Services related to motorcycle engine repairs and maintenance",
        "services": [
            {"name": "Engine oil change", "price": 500, "duration": "30-45 minutes", "warranty": "1 month"},
            {"name": "Clutch plate replacement", "price": 1650, "duration": "1-2 hours", "warranty": "3 months"},
            {"name": "Piston and cylinder repair", "price": 4750, "duration": "2-3 days", "warranty": "6 months"},
            {"name": "Valve clearance adjustment", "price": 850, "duration": "1-2 hours", "warranty": "3 months"},
            {"name": "Engine tuning", "price": 1400, "duration": "1-2 hours", "warranty": "3 months"},
            {"name": "Carburetor cleaning and tuning", "price": 700, "duration": "1-2 hours", "warranty": "2 months"},
            {"name": "Fuel injection system check & service", "price": 2500, "duration": "2-4 hours", "warranty": "3 months"}
        ]
    },
    {
        "category": "Brake System Repairs",
        "description": "Services related to motorcycle brake system maintenance and repairs",
        "services": [
            {"name": "Disc brake pad replacement", "price": 1000, "duration": "30-60 minutes", "warranty": "3 months"},
            {"name": "Drum brake shoe replacement", "price": 550, "duration": "30-60 minutes", "warranty": "3 months"},
            {"name": "Brake fluid replacement", "price": 450, "duration": "30-45 minutes", "warranty": "2 months"},
            {"name": "Brake cable adjustment", "price": 350, "duration": "15-30 minutes", "warranty": "1 month"},
            {"name": "Master cylinder and caliper repair", "price": 1650, "duration": "1-3 hours", "warranty": "3 months"}
        ]
    },
    {
        "category": "Electrical and Battery Work",
        "description": "Services related to motorcycle electrical systems and battery maintenance",
        "services": [
            {"name": "Battery check and replacement", "price": 2750, "duration": "15-30 minutes", "warranty": "Battery warranty as applicable"},
            {"name": "Headlight and taillight repair", "price": 900, "duration": "30-60 minutes", "warranty": "1 month"},
            {"name": "Indicator and horn repair", "price": 450, "duration": "30-45 minutes", "warranty": "1 month"},
            {"name": "Starter motor and alternator testing", "price": 1250, "duration": "30-60 minutes", "warranty": "1 month"},
            {"name": "Wiring and fuse check", "price": 550, "duration": "30-60 minutes", "warranty": "1 month"}
        ]
    },
    {
        "category": "Gear and Transmission",
        "description": "Services related to motorcycle transmission systems and gear mechanisms",
        "services": [
            {"name": "Chain and sprocket replacement", "price": 2250, "duration": "1-2 hours", "warranty": "3 months"},
            {"name": "Gearbox servicing", "price": 3500, "duration": "2-3 hours", "warranty": "3 months"},
            {"name": "Clutch cable adjustment/replacement", "price": 500, "duration": "30-60 minutes", "warranty": "2 months"}
        ]
    },
    {
        "category": "Suspension and Chassis",
        "description": "Services related to motorcycle suspension systems and chassis maintenance",
        "services": [
            {"name": "Front telescopic fork servicing", "price": 1650, "duration": "1-2 hours", "warranty": "3 months"},
            {"name": "Rear shock absorber replacement", "price": 2750, "duration": "1-2 hours", "warranty": "6 months"},
            {"name": "Steering head bearing check", "price": 850, "duration": "30-60 minutes", "warranty": "2 months"}
        ]
    },
    {
        "category": "Tires and Wheels",
        "description": "Services related to motorcycle tires, wheels, and related components",
        "services": [
            {"name": "Tire replacement and puncture repair", "price": 1100, "duration": "30-60 minutes", "warranty": "Material warranty as applicable"},
            {"name": "Wheel balancing and alignment", "price": 1000, "duration": "30-60 minutes", "warranty": "1 month"}
        ]
    },
    {
        "category": "Fuel System Repairs",
        "description": "Services related to motorcycle fuel system maintenance and repairs",
        "services": [
            {"name": "Fuel pipe and filter check", "price": 550, "duration": "30-60 minutes", "warranty": "1 month"},
            {"name": "Petrol tank leakage repair", "price": 2000, "duration": "1-3 hours", "warranty": "3 months"}
        ]
    },
    {
        "category": "Exhaust System Repairs",
        "description": "Services related to motorcycle exhaust system maintenance and repairs",
        "services": [
            {"name": "Silencer cleaning and repair", "price": 1250, "duration": "30-60 minutes", "warranty": "2 months"},
            {"name": "Catalytic converter check", "price": 2250, "duration": "1-2 hours", "warranty": "1 month"}
        ]
    },
    {
        "category": "Other General Services",
        "description": "General motorcycle maintenance and inspection services",
        "services": [
            {"name": "Bike washing and polishing", "price": 500, "duration": "30-60 minutes", "warranty": "Service only"},
            {"name": "Nut and bolt tightening", "price": 325, "duration": "15-30 minutes", "warranty": "Service only"},
            {"name": "Test ride and performance check", "price": 450, "duration": "30-45 minutes", "warranty": "Service only"}
        ]
    }
]

def create_categories_and_services():
    categories_created = 0
    services_created = 0
    
    for item in service_data:
        # Create or get the category
        category_name = item["category"]
        category_slug = category_name.lower().replace(' ', '-')
        
        category, created = ServiceCategory.objects.get_or_create(
            name=category_name,
            defaults={
                'slug': category_slug,
                'description': item["description"]
            }
        )
        
        if created:
            categories_created += 1
            print(f"Created category: {category.name}")
        else:
            print(f"Using existing category: {category.name}")
        
        # Create services for this category
        for service_item in item["services"]:
            service_name = service_item["name"]
            service_slug = service_name.lower().replace(' ', '-')
            
            service, service_created = Service.objects.get_or_create(
                name=service_name,
                category=category,
                defaults={
                    'slug': service_slug,
                    'description': f"{service_name} service for motorcycles",
                    'base_price': decimal.Decimal(str(service_item["price"])),
                    'duration': service_item["duration"],
                    'warranty': service_item["warranty"]
                }
            )
            
            if service_created:
                services_created += 1
                print(f"  - Created service: {service.name} (₹{service.base_price})")
    
    print(f"\nSummary: Created {categories_created} categories and {services_created} services")

if __name__ == "__main__":
    print("Starting to create service categories and services...")
    create_categories_and_services()
    print("Finished creating service categories and services!") 