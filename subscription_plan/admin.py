from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils import timezone
from .models import Plan, PlanVariant, SubscriptionRequest, UserSubscription, VisitSchedule


class PlanVariantInline(admin.TabularInline):
    model = PlanVariant
    extra = 1
    fields = ('duration_type', 'price', 'discounted_price', 'max_visits', 'is_active')


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'plan_type', 'description', 'is_active', 'created_at')
    list_filter = ('plan_type', 'is_active')
    search_fields = ('name', 'description')
    inlines = [PlanVariantInline]
    
    fieldsets = (
        (None, {
            'fields': ('name', 'plan_type', 'description', 'is_active')
        }),
        ('Features', {
            'fields': ('features_text',),
            'description': 'Enter features as comma-separated values'
        }),
    )


@admin.register(PlanVariant)
class PlanVariantAdmin(admin.ModelAdmin):
    list_display = ('plan', 'duration_type', 'price', 'discounted_price', 'max_visits', 'is_active')
    list_filter = ('plan', 'duration_type', 'is_active')
    search_fields = ('plan__name',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(SubscriptionRequest)
class SubscriptionRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan_display', 'duration_display', 'request_date', 'status', 'service_request_link')
    list_filter = ('status', 'request_date', 'plan_variant__plan')
    search_fields = ('user__username', 'user__email', 'customer_name', 'customer_email')
    readonly_fields = ('request_date', 'service_request_link')
    
    fieldsets = (
        (None, {
            'fields': ('user', 'plan_variant', 'status', 'request_date', 'approval_date', 'rejection_reason')
        }),
        ('Service Request', {
            'fields': ('service_request', 'service_request_link'),
            'classes': ('collapse',)
        }),
        ('Admin Notes', {
            'fields': ('admin_notes',),
            'classes': ('collapse',)
        }),
        ('Vehicle Information', {
            'fields': ('vehicle_type', 'manufacturer', 'vehicle_model'),
            'classes': ('collapse',)
        }),
        ('Customer Information', {
            'fields': ('customer_name', 'customer_email', 'customer_phone', 'address', 'city', 'state', 'postal_code'),
            'classes': ('collapse',)
        })
    )
    
    def plan_display(self, obj):
        return obj.plan_variant.plan.name
    plan_display.short_description = 'Plan'
    
    def duration_display(self, obj):
        return obj.plan_variant.get_duration_type_display()
    duration_display.short_description = 'Duration'
    
    def service_request_link(self, obj):
        if obj.service_request:
            url = reverse('admin:repairing_service_servicerequest_change', args=[obj.service_request.id])
            return format_html('<a href="{}">View Service Request #{}</a>', url, obj.service_request.id)
        return "No linked service request"
    service_request_link.short_description = 'Service Request'
    
    actions = ['approve_requests', 'reject_requests']
    
    def approve_requests(self, request, queryset):
        count = 0
        for subscription_request in queryset.filter(status=SubscriptionRequest.PENDING):
            subscription_request.approve()
            count += 1
        self.message_user(request, f"{count} subscription requests were approved.")
    approve_requests.short_description = "Approve selected subscription requests"
    
    def reject_requests(self, request, queryset):
        count = 0
        for subscription_request in queryset.filter(status=SubscriptionRequest.PENDING):
            subscription_request.reject("Rejected via admin bulk action")
            count += 1
        self.message_user(request, f"{count} subscription requests were rejected.")
    reject_requests.short_description = "Reject selected subscription requests"


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan_display', 'duration_display', 'start_date', 'end_date', 'status', 'remaining_visits')
    list_filter = ('status', 'start_date', 'end_date')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
    
    def plan_display(self, obj):
        return obj.plan_variant.plan.name
    plan_display.short_description = 'Plan'
    
    def duration_display(self, obj):
        return obj.plan_variant.get_duration_type_display()
    duration_display.short_description = 'Duration'
    
    actions = ['cancel_subscriptions']
    
    def cancel_subscriptions(self, request, queryset):
        count = 0
        for subscription in queryset.filter(status=UserSubscription.ACTIVE):
            subscription.cancel()
            count += 1
        self.message_user(request, f"{count} subscriptions were cancelled.")
    cancel_subscriptions.short_description = "Cancel selected subscriptions"


@admin.register(VisitSchedule)
class VisitScheduleAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'subscription', 'customer_name', 'scheduled_date', 
        'status', 'completion_date', 'remaining_visits'
    ]
    list_filter = ['status', 'scheduled_date', 'completion_date']
    search_fields = [
        'subscription__user__username', 'subscription__user__email',
        'technician_notes', 'service_notes'
    ]
    readonly_fields = ['completion_date']
    actions = ['mark_as_completed', 'mark_as_cancelled']
    
    def customer_name(self, obj):
        return f"{obj.subscription.user.get_full_name() or obj.subscription.user.username}"
    customer_name.short_description = 'Customer'
    
    def remaining_visits(self, obj):
        return obj.subscription.remaining_visits
    remaining_visits.short_description = 'Remaining Visits'
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if not obj:  # Only for new visits
            # Filter to show only active subscriptions
            form.base_fields['subscription'].queryset = UserSubscription.objects.filter(
                status='ACTIVE',
                end_date__gt=timezone.now()
            )
        return form
    
    def save_model(self, request, obj, form, change):
        if not change:  # Only for new visits
            # Validate remaining visits
            if obj.subscription.remaining_visits <= 0:
                self.message_user(request, "No remaining visits in subscription", level='ERROR')
                return
            
            # Check for existing visits on same date
            existing_visit = VisitSchedule.objects.filter(
                subscription=obj.subscription,
                scheduled_date=obj.scheduled_date,
                status=VisitSchedule.SCHEDULED
            ).exists()
            
            if existing_visit:
                self.message_user(request, "Already have a visit scheduled for this date", level='ERROR')
                return
        
        super().save_model(request, obj, form, change)
    
    @admin.action(description='Mark selected visits as completed')
    def mark_as_completed(self, request, queryset):
        for visit in queryset.filter(status=VisitSchedule.SCHEDULED):
            subscription = visit.subscription
            
            # Check if subscription has remaining visits
            if subscription.remaining_visits > 0:
                # Update visit
                visit.status = VisitSchedule.COMPLETED
                visit.completion_date = timezone.now()
                visit.save()
                
                # Update subscription
                subscription.remaining_visits -= 1
                subscription.last_visit_date = timezone.now()
                subscription.save()
                
                self.message_user(
                    request, 
                    f"Visit {visit.id} completed. Remaining visits: {subscription.remaining_visits}"
                )
            else:
                self.message_user(
                    request,
                    f"Visit {visit.id} not completed. No remaining visits in subscription.",
                    level='ERROR'
                )
    
    @admin.action(description='Mark selected visits as cancelled')
    def mark_as_cancelled(self, request, queryset):
        updated = queryset.filter(status=VisitSchedule.SCHEDULED).update(
            status=VisitSchedule.CANCELLED
        )
        self.message_user(request, f"{updated} visits were cancelled.")
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "subscription":
            kwargs["queryset"] = UserSubscription.objects.filter(
                status='ACTIVE',
                end_date__gt=timezone.now()
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
