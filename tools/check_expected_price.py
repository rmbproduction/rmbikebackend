#!/usr/bin/env python
"""
Script to check expected_price values in all vehicles in the database
"""

import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'authback.settings')
django.setup()

from marketplace.models import Vehicle

def check_expected_price():
    """Check all vehicles for expected_price values and report issues"""
    print("\n===== EXPECTED PRICE CHECK =====")
    
    # Get all vehicles
    vehicles = Vehicle.objects.all().order_by('-created_at')
    print(f"Found {vehicles.count()} vehicles in the database")
    
    # Track statistics
    missing_expected_price = 0
    zero_expected_price = 0
    valid_expected_price = 0
    
    # Check each vehicle
    for index, vehicle in enumerate(vehicles):
        if vehicle.expected_price is None:
            print(f"❌ Vehicle ID {vehicle.id} ({vehicle.registration_number}): Missing expected_price")
            missing_expected_price += 1
        elif vehicle.expected_price == 0:
            print(f"⚠️ Vehicle ID {vehicle.id} ({vehicle.registration_number}): expected_price is zero")
            zero_expected_price += 1
        else:
            print(f"✅ Vehicle ID {vehicle.id} ({vehicle.registration_number}): expected_price = {vehicle.expected_price}")
            valid_expected_price += 1
    
    # Print summary
    print("\n===== SUMMARY =====")
    print(f"Total vehicles: {vehicles.count()}")
    print(f"Valid expected_price: {valid_expected_price}")
    print(f"Zero expected_price: {zero_expected_price}")
    print(f"Missing expected_price: {missing_expected_price}")
    
    # Print recommendation
    if missing_expected_price > 0:
        print("\n⚠️ You have vehicles with missing expected_price values. Use the fix-expected-price.py script to repair them.")

if __name__ == "__main__":
    check_expected_price() 