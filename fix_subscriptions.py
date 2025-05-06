#!/usr/bin/env python
import os
import sys
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'authback.settings')
django.setup()

from repairing_service.models import SubscriptionBooking, SubscriptionPlanOption, SubscriptionPlan
from vehicle.models import UserVehicle

def fix_subscription_records():
    # Get all subscription bookings with null plan_option or vehicle
    broken_subscriptions = SubscriptionBooking.objects.filter(
        plan_option__isnull=True
    ).select_related('user')
    
    print(f"Found {broken_subscriptions.count()} subscription bookings with null plan_option")
    
    if broken_subscriptions.count() == 0:
        print("No broken subscription bookings found. All good!")
        return
    
    # Get or create a default plan option to use
    try:
        default_plan_option = SubscriptionPlanOption.objects.first()
        if not default_plan_option:
            # Create a default plan and option
            default_plan = SubscriptionPlan.objects.create(
                name='Default Plan',
                description='Default plan for existing bookings'
            )
            default_plan_option = SubscriptionPlanOption.objects.create(
                plan=default_plan,
                duration='3 months',
                price=0,
                max_services=1
            )
            print(f"Created default plan option: {default_plan_option}")
        else:
            print(f"Using existing plan option: {default_plan_option}")
    except Exception as e:
        print(f"Error creating default plan option: {e}")
        return
    
    # Fix subscription bookings with null plan_option
    for subscription in broken_subscriptions:
        try:
            # Try to find a suitable vehicle for the user
            if subscription.vehicle is None:
                user_vehicle = UserVehicle.objects.filter(user=subscription.user).first()
                if user_vehicle:
                    subscription.vehicle = user_vehicle
                    print(f"Assigned vehicle to subscription for user {subscription.user}")
                else:
                    print(f"Warning: No vehicle found for user {subscription.user}")
                    # You may decide to create a default vehicle here or handle differently
            
            # Assign the default plan option
            subscription.plan_option = default_plan_option
            subscription.save()
            print(f"Fixed subscription {subscription.id} for user {subscription.user}")
        except Exception as e:
            print(f"Error fixing subscription {subscription.id}: {e}")
    
    print("Subscription fixing process completed!")

if __name__ == "__main__":
    print("Starting subscription fixing script...")
    fix_subscription_records()
    print("Script completed.") 