from django.core.management.base import BaseCommand
from repairing_service.models import PricingPlan, AdditionalService, PricingPlanFeature

class Command(BaseCommand):
    help = 'Seeds the database with initial pricing data'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Seeding pricing data...'))

        # Create pricing plans
        basic_service = PricingPlan.objects.create(
            name='Basic Service',
            price=49,
            duration='2-3 Hours',
            description='Essential maintenance for regular riders',
            recommended=False
        )
        PricingPlanFeature.objects.create(pricing_plan=basic_service, name='Basic Safety Inspection')
        PricingPlanFeature.objects.create(pricing_plan=basic_service, name='Tire Pressure Check')
        PricingPlanFeature.objects.create(pricing_plan=basic_service, name='Chain Lubrication')
        PricingPlanFeature.objects.create(pricing_plan=basic_service, name='Brake Adjustment')
        PricingPlanFeature.objects.create(pricing_plan=basic_service, name='Gear Tuning')

        premium_service = PricingPlan.objects.create(
            name='Premium Service',
            price=99,
            duration='3-4 Hours',
            description='Comprehensive care for enthusiast riders',
            recommended=True
        )
        PricingPlanFeature.objects.create(pricing_plan=premium_service, name='Full Safety Inspection')
        PricingPlanFeature.objects.create(pricing_plan=premium_service, name='Wheel Truing')
        PricingPlanFeature.objects.create(pricing_plan=premium_service, name='Drivetrain Cleaning')
        PricingPlanFeature.objects.create(pricing_plan=premium_service, name='Brake Bleeding')
        PricingPlanFeature.objects.create(pricing_plan=premium_service, name='Cable Replacement')
        PricingPlanFeature.objects.create(pricing_plan=premium_service, name='Frame Cleaning')
        PricingPlanFeature.objects.create(pricing_plan=premium_service, name='Suspension Check')

        pro_service = PricingPlan.objects.create(
            name='Pro Service',
            price=149,
            duration='4-5 Hours',
            description='Ultimate care for professional bikes',
            recommended=False
        )
        PricingPlanFeature.objects.create(pricing_plan=pro_service, name='Complete Bike Overhaul')
        PricingPlanFeature.objects.create(pricing_plan=pro_service, name='Fork Service')
        PricingPlanFeature.objects.create(pricing_plan=pro_service, name='Bearing Replacement')
        PricingPlanFeature.objects.create(pricing_plan=pro_service, name='Frame Alignment')
        PricingPlanFeature.objects.create(pricing_plan=pro_service, name='Custom Tuning')
        PricingPlanFeature.objects.create(pricing_plan=pro_service, name='Performance Testing')
        PricingPlanFeature.objects.create(pricing_plan=pro_service, name='Parts Upgrade Consultation')
        PricingPlanFeature.objects.create(pricing_plan=pro_service, name='3-Month Warranty')

        # Create additional services
        AdditionalService.objects.create(
            name='Parts Replacement',
            price='Varies',
            description='Quality replacement parts with warranty'
        )
        AdditionalService.objects.create(
            name='Emergency Service',
            price='+$30',
            description='24/7 emergency repair service'
        )
        AdditionalService.objects.create(
            name='Extended Warranty',
            price='+$19',
            description='Additional 3 months of coverage'
        )
        AdditionalService.objects.create(
            name='Custom Upgrades',
            price='Varies',
            description='Performance-focused modifications'
        )

        self.stdout.write(self.style.SUCCESS('Pricing data seeded successfully!'))
