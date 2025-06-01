from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.db.models import Count, Sum
from django.utils import timezone
from datetime import timedelta
from vehicle.models import UserVehicle
from marketplace.models import SellRequest
from repairing_service.models import ServiceRequest
from subscription_plan.models import SubscriptionRequest, VisitSchedule
from django.contrib.auth import get_user_model

User = get_user_model()

@staff_member_required
def admin_dashboard(request):
    # Get date ranges
    today = timezone.now().date()
    last_30_days = today - timedelta(days=30)
    
    # User statistics
    total_users = User.objects.count()
    new_users_30d = User.objects.filter(date_joined__date__gte=last_30_days).count()
    active_users = User.objects.filter(is_active=True).count()

    # Vehicle statistics
    total_vehicles = UserVehicle.objects.count()
    vehicles_for_sale = SellRequest.objects.filter(status='active').count()

    # Service statistics
    total_services = ServiceRequest.objects.count()
    pending_services = ServiceRequest.objects.filter(status='pending').count()
    completed_services = ServiceRequest.objects.filter(status='completed').count()

    # Subscription statistics
    active_subscriptions = SubscriptionRequest.objects.filter(status='approved').count()
    pending_subscriptions = SubscriptionRequest.objects.filter(status='pending').count()
    
    # Visit statistics
    upcoming_visits = VisitSchedule.objects.filter(
        scheduled_date__gte=today,
        status='scheduled'
    ).count()
    completed_visits = VisitSchedule.objects.filter(status='completed').count()

    # Monthly trends
    monthly_users = User.objects.filter(
        date_joined__date__gte=last_30_days
    ).extra(
        select={'day': 'date(date_joined)'}
    ).values('day').annotate(count=Count('id')).order_by('day')

    monthly_services = ServiceRequest.objects.filter(
        created_at__date__gte=last_30_days
    ).extra(
        select={'day': 'date(created_at)'}
    ).values('day').annotate(count=Count('id')).order_by('day')

    context = {
        'total_users': total_users,
        'new_users_30d': new_users_30d,
        'active_users': active_users,
        'total_vehicles': total_vehicles,
        'vehicles_for_sale': vehicles_for_sale,
        'total_services': total_services,
        'pending_services': pending_services,
        'completed_services': completed_services,
        'active_subscriptions': active_subscriptions,
        'pending_subscriptions': pending_subscriptions,
        'upcoming_visits': upcoming_visits,
        'completed_visits': completed_visits,
        'monthly_users': list(monthly_users),
        'monthly_services': list(monthly_services),
    }

    return render(request, 'admin_panel/dashboard.html', context)

@staff_member_required
def service_analytics(request):
    # Service category distribution
    category_distribution = ServiceRequest.objects.values(
        'service_category__name'
    ).annotate(
        count=Count('id')
    ).order_by('-count')

    # Status distribution
    status_distribution = ServiceRequest.objects.values(
        'status'
    ).annotate(
        count=Count('id')
    ).order_by('-count')

    context = {
        'category_distribution': category_distribution,
        'status_distribution': status_distribution,
    }

    return render(request, 'admin_panel/service_analytics.html', context)

@staff_member_required
def subscription_analytics(request):
    # Plan distribution
    plan_distribution = SubscriptionRequest.objects.values(
        'plan_variant__plan__name'
    ).annotate(
        count=Count('id')
    ).order_by('-count')

    # Visit analytics
    visit_status = VisitSchedule.objects.values(
        'status'
    ).annotate(
        count=Count('id')
    ).order_by('-count')

    context = {
        'plan_distribution': plan_distribution,
        'visit_status': visit_status,
    }

    return render(request, 'admin_panel/subscription_analytics.html', context) 