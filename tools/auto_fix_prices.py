#!/usr/bin/env python
"""
Non-interactive script to set demo expected_price values for vehicles
"""

import os
import sys
import django
import random
from decimal import Decimal

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'authback.settings')
django.setup()

from marketplace.models import Vehicle

def auto_set_demo_prices():
    """
    Automatically set reasonable expected_price values for vehicles
    This is for demo purposes only.
    
    IMPORTANT: expected_price is the seller's expected price
               price is the admin's counter-offer price
    """
    print("\n===== SETTING DEMO EXPECTED PRICES =====")
    
    # Get all vehicles
    vehicles = Vehicle.objects.all().order_by('-created_at')
    print(f"Found {vehicles.count()} vehicles")
    
    # Define price ranges by vehicle type
    price_ranges = {
        'bike': (40000, 200000),  # 40k-200k for standard bikes
        'scooter': (30000, 120000),  # 30k-120k for scooters
        'electric_bike': (60000, 250000),  # 60k-250k for electric bikes
        'electric_scooter': (50000, 180000),  # 50k-180k for electric scooters
    }
    
    # Default range if vehicle type not in the dictionary
    default_range = (40000, 150000)
    
    updated_count = 0
    
    for vehicle in vehicles:
        # Determine price range based on vehicle type
        price_range = price_ranges.get(vehicle.vehicle_type, default_range)
        
        # Generate a random price in the appropriate range
        base_price = random.randint(price_range[0], price_range[1])
        
        # Adjust based on year (newer = more expensive)
        current_year = 2025
        age_factor = 1.0 - (0.05 * (current_year - vehicle.year))  # 5% depreciation per year
        age_factor = max(0.6, age_factor)  # At most 40% depreciation
        
        adjusted_price = int(base_price * age_factor)
        
        # Round to nearest thousand
        expected_price = round(adjusted_price / 1000) * 1000
        
        # We're only setting expected_price, not price
        # IMPORTANT DISTINCTION:
        # expected_price: The price expected by the seller when submitting their vehicle
        # price: The counter price set by admin for marketplace listing
        
        print(f"Vehicle {vehicle.id} ({vehicle.registration_number}): Setting expected_price to {expected_price}")
        vehicle.expected_price = Decimal(expected_price)
        vehicle.save(update_fields=['expected_price'])
        updated_count += 1
    
    print(f"\n✅ Updated expected_price for {updated_count} vehicles")

    # Verify all vehicles now have expected_price set
    missing_count = Vehicle.objects.filter(expected_price__isnull=True).count()
    if missing_count > 0:
        print(f"⚠️ Warning: {missing_count} vehicles still have null expected_price")
    else:
        print("✅ All vehicles now have expected_price set")

if __name__ == "__main__":
    print("Auto-setting demo expected_price values for all vehicles")
    auto_set_demo_prices() 