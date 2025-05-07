from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.utils import timezone
from django.db.models import Count, Sum
from datetime import timedelta
from repairing_service.models import ServiceRequest
from subscription_plan.models import Subscription
from vehicle.models import Vehicle
from accounts.models import User
from django.contrib.admin.models import LogEntry

@staff_member_required
def admin_dashboard(request):
    # Get current date and time
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Service Requests Statistics
    total_service_requests = ServiceRequest.objects.count()
    active_service_requests = ServiceRequest.objects.filter(status='in_progress').count()
    completed_today = ServiceRequest.objects.filter(
        completion_date__gte=today_start,
        status='completed'
    ).count()

    # Subscription Statistics
    total_subscriptions = Subscription.objects.count()
    active_subscriptions = Subscription.objects.filter(
        end_date__gte=now,
        status='active'
    ).count()
    monthly_revenue = Subscription.objects.filter(
        start_date__gte=month_start
    ).aggregate(total=Sum('plan__price'))['total'] or 0

    # Vehicle Statistics
    total_vehicles = Vehicle.objects.count()
    new_vehicles_today = Vehicle.objects.filter(created_at__gte=today_start).count()
    premium_vehicles = Vehicle.objects.filter(is_premium=True).count()

    # User Statistics
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    staff_count = User.objects.filter(is_staff=True).count()

    # Popular Plans Data
    plan_data = Subscription.objects.values('plan__name').annotate(
        count=Count('id')
    ).order_by('-count')[:5]
    plan_labels = [item['plan__name'] for item in plan_data]
    plan_counts = [item['count'] for item in plan_data]

    # Recent Activities
    recent_activities = LogEntry.objects.select_related('content_type', 'user')[:10]

    context = {
        'total_service_requests': total_service_requests,
        'active_service_requests': active_service_requests,
        'completed_today': completed_today,
        'total_subscriptions': total_subscriptions,
        'active_subscriptions': active_subscriptions,
        'monthly_revenue': monthly_revenue,
        'total_vehicles': total_vehicles,
        'new_vehicles_today': new_vehicles_today,
        'premium_vehicles': premium_vehicles,
        'total_users': total_users,
        'active_users': active_users,
        'staff_count': staff_count,
        'plan_labels': plan_labels,
        'plan_data': plan_counts,
        'recent_activities': recent_activities,
    }

    return render(request, 'admin/dashboard.html', context) 