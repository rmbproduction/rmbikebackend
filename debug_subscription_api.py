#!/usr/bin/env python
import os
import sys
import django
import traceback
from django.utils import timezone
from subscription_plan.models import SubscriptionRequest, UserSubscription
from django.contrib.auth import get_user_model

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'authback.settings')
django.setup()

from repairing_service.models import SubscriptionPlan, SubscriptionPlanOption, PlanService
from repairing_service.serializers import SubscriptionPlanSerializer

def debug_subscription_plans_api():
    print("Debugging subscription plans API...")
    
    try:
        # Step 1: Check if there are any subscription plans in the database
        plans = SubscriptionPlan.objects.all()
        print(f"Found {plans.count()} subscription plans")
        
        # Step 2: Try to prefetch related data (this is what the view does)
        plans_with_related = SubscriptionPlan.objects.all().prefetch_related('options__services')
        print(f"Successfully fetched plans with related data: {plans_with_related.count()}")
        
        # Step 3: Test serialization
        for plan in plans_with_related:
            print(f"\nPlan: {plan.name}")
            
            # Check if options exist
            options = plan.options.all()
            print(f"Options count: {options.count()}")
            
            for option in options:
                print(f"  Option: {option.duration}, Services: {option.services.count()}")
                
                # Check services
                for service in option.services.all():
                    print(f"    Service: {service}")
        
        # Step 4: Test the serializer directly
        print("\nTesting serializer...")
        try:
            serializer = SubscriptionPlanSerializer(plans_with_related, many=True)
            serialized_data = serializer.data
            print(f"Serialization successful! Generated {len(serialized_data)} plan objects")
        except Exception as e:
            print(f"Serialization error: {e}")
            traceback.print_exc()
            
    except Exception as e:
        print(f"Error encountered: {e}")
        traceback.print_exc()

def debug_subscription_approval():
    # Get all pending subscription requests
    pending_requests = SubscriptionRequest.objects.filter(status=SubscriptionRequest.PENDING)
    print(f"Found {pending_requests.count()} pending requests")
    
    for request in pending_requests:
        print(f"\nChecking request {request.id} for user {request.user.username}")
        
        # Check if user already has active subscription
        active_subs = UserSubscription.objects.filter(
            user=request.user,
            status=UserSubscription.ACTIVE
        )
        print(f"User has {active_subs.count()} active subscriptions")
        
        # Try approving the request
        try:
            print("Attempting to approve request...")
            request.approve()
            print("Request approved successfully")
            
            # Verify subscription was created
            new_sub = UserSubscription.objects.filter(
                user=request.user,
                plan_variant=request.plan_variant,
                status=UserSubscription.ACTIVE
            ).order_by('-created_at').first()
            
            if new_sub:
                print(f"New subscription created: {new_sub.id}")
                print(f"Start date: {new_sub.start_date}")
                print(f"End date: {new_sub.end_date}")
                print(f"Remaining visits: {new_sub.remaining_visits}")
            else:
                print("ERROR: No subscription was created!")
                
        except Exception as e:
            print(f"Error during approval: {str(e)}")

if __name__ == "__main__":
    print("Starting subscription plans API debug script...")
    debug_subscription_plans_api()
    print("\nScript completed.")
    debug_subscription_approval() 