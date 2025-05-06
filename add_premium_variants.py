import os
import django
import decimal

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'authback.settings')
django.setup()

# Import models
from subscription_plan.models import Plan, PlanVariant

def create_premium_variants():
    """
    Create premium plan variants with different durations
    """
    try:
        # Find the premium plan
        premium_plan = Plan.objects.get(plan_type='premium')
        print(f"Found premium plan: {premium_plan.name} (ID: {premium_plan.id})")
        
        # Define variants for different durations with direct original and discounted prices
        variants_data = [
            # Half-yearly variants
            {
                "duration_type": PlanVariant.HALF_YEARLY,
                "price": decimal.Decimal('1499.00'),
                "discounted_price": decimal.Decimal('1274.15'),  # ~15% off
                "max_visits": 4,
            },
            {
                "duration_type": PlanVariant.HALF_YEARLY,
                "price": decimal.Decimal('2499.00'),
                "discounted_price": decimal.Decimal('2124.15'),  # ~15% off
                "max_visits": 8,
            },
            {
                "duration_type": PlanVariant.HALF_YEARLY,
                "price": decimal.Decimal('3599.00'),
                "discounted_price": decimal.Decimal('3059.15'),  # ~15% off
                "max_visits": 12,
            },
            # Yearly variants
            {
                "duration_type": PlanVariant.YEARLY,
                "price": decimal.Decimal('2499.00'),
                "discounted_price": decimal.Decimal('1999.20'),  # ~20% off
                "max_visits": 6,
            },
            {
                "duration_type": PlanVariant.YEARLY,
                "price": decimal.Decimal('3999.00'),
                "discounted_price": decimal.Decimal('3199.20'),  # ~20% off
                "max_visits": 12,
            },
            {
                "duration_type": PlanVariant.YEARLY,
                "price": decimal.Decimal('5999.00'),
                "discounted_price": decimal.Decimal('4799.20'),  # ~20% off
                "max_visits": 24,
            },
        ]
        
        # Create each variant
        created_variants = []
        for data in variants_data:
            variant = PlanVariant(
                plan=premium_plan,
                duration_type=data['duration_type'],
                price=data['price'],
                discounted_price=data['discounted_price'],
                max_visits=data['max_visits'],
                is_active=True
            )
            variant.save()
            created_variants.append(variant)
            print(f"Created variant: {variant}")
        
        print(f"\nSuccessfully created {len(created_variants)} premium plan variants")
        
    except Plan.DoesNotExist:
        print("Error: Premium plan does not exist. Please create it first.")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    create_premium_variants() 