from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
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
        }),
        ('Schedule Information', {
            'fields': ('schedule_date', 'schedule_time'),
            'classes': ('collapse',)
        }),
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
    list_display = ('subscription_display', 'scheduled_date', 'status', 'completion_date')
    list_filter = ('status', 'scheduled_date', 'completion_date')
    search_fields = ('subscription__user__username', 'subscription__user__email', 'service_notes')
    readonly_fields = ('created_at', 'updated_at')
    
    def subscription_display(self, obj):
        return f"{obj.subscription.user.username} - {obj.subscription.plan_variant.plan.name}"
    subscription_display.short_description = 'Subscription'
    
    actions = ['complete_visits', 'cancel_visits']
    
    def complete_visits(self, request, queryset):
        count = 0
        for visit in queryset.filter(status=VisitSchedule.SCHEDULED):
            visit.complete("Completed via admin bulk action")
            count += 1
        self.message_user(request, f"{count} visits were marked as completed.")
    complete_visits.short_description = "Mark selected visits as completed"
    
    def cancel_visits(self, request, queryset):
        count = 0
        for visit in queryset.filter(status=VisitSchedule.SCHEDULED):
            visit.cancel("Cancelled via admin bulk action")
            count += 1
        self.message_user(request, f"{count} visits were cancelled.")
    cancel_visits.short_description = "Cancel selected visits"
