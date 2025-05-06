#!/usr/bin/env python
"""
Script to fix missing expected_price values in the database
This will set expected_price equal to price for any vehicle where expected_price is missing
"""

import os
import sys
import django
from decimal import Decimal
import random

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'authback.settings')
django.setup()

from marketplace.models import Vehicle
from django.db.models import Q

def fix_expected_price():
    """Find and fix all vehicles with missing expected_price values"""
    print("\n===== EXPECTED PRICE FIXER =====")
    
    # Find vehicles with missing or zero expected_price
    problem_vehicles = Vehicle.objects.filter(
        Q(expected_price__isnull=True) | Q(expected_price=0)
    ).order_by('-created_at')
    
    print(f"Found {problem_vehicles.count()} vehicles needing expected_price fixes")
    
    # Track statistics
    fixed_count = 0
    skipped_count = 0
    
    for vehicle in problem_vehicles:
        # Print vehicle info
        print(f"\nVehicle ID: {vehicle.id}")
        print(f"Registration: {vehicle.registration_number}")
        print(f"Current price: {vehicle.price}")
        print(f"Current expected_price: {vehicle.expected_price}")
        
        # Determine the fix value
        if vehicle.price and vehicle.price > 0:
            # Use price as expected_price
            fix_value = vehicle.price
            print(f"Will set expected_price = {fix_value} (from price)")
            
            # Update the vehicle
            vehicle.expected_price = fix_value
            vehicle.save(update_fields=['expected_price'])
            print(f"✅ Fixed: Vehicle ID {vehicle.id} expected_price set to {fix_value}")
            fixed_count += 1
        else:
            # No good value to use
            print(f"⚠️ Skipped: Vehicle ID {vehicle.id} - no valid price to use")
            skipped_count += 1
    
    # Print summary
    print("\n===== SUMMARY =====")
    print(f"Total vehicles checked: {problem_vehicles.count()}")
    print(f"Vehicles fixed: {fixed_count}")
    print(f"Vehicles skipped: {skipped_count}")
    
    # Final message
    if fixed_count > 0:
        print("\n✅ Expected price fix completed successfully!")
    else:
        print("\n⚠️ No vehicles were updated.")

def set_demo_prices():
    """
    Set reasonable demonstration prices for vehicles with zero price and expected_price
    Only for test/demo purposes
    """
    print("\n===== SETTING DEMO PRICES =====")
    
    # Find vehicles with zero prices
    zero_price_vehicles = Vehicle.objects.filter(
        Q(price=0) & Q(expected_price=0)
    ).order_by('-created_at')
    
    print(f"Found {zero_price_vehicles.count()} vehicles with zero prices")
    
    # Get price ranges based on vehicle type
    price_ranges = {
        'bike': (40000, 200000),  # 40k-200k for standard bikes
        'scooter': (30000, 120000),  # 30k-120k for scooters
        'electric_bike': (60000, 250000),  # 60k-250k for electric bikes
        'electric_scooter': (50000, 180000),  # 50k-180k for electric scooters
    }
    
    # Default range if vehicle type not in the dictionary
    default_range = (40000, 150000)
    
    fixed_count = 0
    
    for vehicle in zero_price_vehicles:
        # Determine price range based on vehicle type
        price_range = price_ranges.get(vehicle.vehicle_type, default_range)
        
        # Generate a random price in the appropriate range
        base_price = random.randint(price_range[0], price_range[1])
        
        # Adjust based on year (newer = more expensive)
        current_year = 2025  # Using the year from the migration file
        age_factor = 1.0 - (0.05 * (current_year - vehicle.year))  # 5% depreciation per year
        age_factor = max(0.6, age_factor)  # At most 40% depreciation
        
        adjusted_price = int(base_price * age_factor)
        
        # Round to nearest thousand
        final_price = round(adjusted_price / 1000) * 1000
        
        # Set a slightly higher expected_price (seller usually wants more)
        expected_price = int(final_price * 1.1)  # 10% higher
        expected_price = round(expected_price / 1000) * 1000  # Round to nearest thousand
        
        print(f"\nVehicle ID: {vehicle.id}")
        print(f"Registration: {vehicle.registration_number}")
        print(f"Type: {vehicle.vehicle_type}, Year: {vehicle.year}")
        print(f"Setting price to {final_price} and expected_price to {expected_price}")
        
        # Update the vehicle
        vehicle.price = Decimal(final_price)
        vehicle.expected_price = Decimal(expected_price)
        vehicle.save(update_fields=['price', 'expected_price'])
        print(f"✅ Updated Vehicle ID {vehicle.id} with demo prices")
        fixed_count += 1
    
    print(f"\n✅ Updated {fixed_count} vehicles with demo pricing")

if __name__ == "__main__":
    # Ask for confirmation
    response = input("This will fix expected_price values and set demo prices. Continue? (y/n): ")
    if response.lower() == 'y':
        fix_expected_price()
        # After fixing missing expected prices, set demo prices for any that are still zero
        set_demo_prices()
    else:
        print("Operation cancelled.") 