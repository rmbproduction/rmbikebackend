# admin.py
from django.contrib import admin
from django.db import models
from django.forms import Textarea
from django.urls import reverse
from django.utils.html import format_html
from .models import (
    Feature, ServiceCategory, Service, ServicePrice, Cart, CartItem,
    ServiceRequest, FieldStaff, ServiceRequestResponse, LiveLocation,
    DistancePricingRule, PricingPlan, PricingPlanFeature, AdditionalService
)

@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'image')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'base_price', 'discounted_price', 'duration', 'warranty', 'recommended')
    list_filter = ('category', 'recommended')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    filter_horizontal = ('manufacturers', 'vehicles_models', 'features')
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 10, 'cols': 80})},
    }

@admin.register(ServicePrice)
class ServicePriceAdmin(admin.ModelAdmin):
    list_display = ('service', 'manufacturer', 'vehicle_model', 'price')
    list_filter = ('service', 'manufacturer', 'vehicle_model')
    search_fields = ('service__name', 'manufacturer__name', 'vehicle_model__name')

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_items_count')
    
    def get_items_count(self, obj):
        return obj.cartitem_set.count()
    get_items_count.short_description = 'Number of Items'

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('cart', 'service', 'quantity')
    list_filter = ('cart', 'service')

@admin.register(DistancePricingRule)
class DistancePricingRuleAdmin(admin.ModelAdmin):
    list_display = ('id', 'service_center_latitude', 'service_center_longitude', 'free_radius_km', 'per_km_charge', 'base_charge', 'is_active')
    list_editable = ('service_center_latitude', 'service_center_longitude', 'free_radius_km', 'per_km_charge', 'base_charge', 'is_active')
    list_filter = ('is_active',)

@admin.register(PricingPlan)
class PricingPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'duration', 'recommended')
    list_filter = ('recommended',)
    search_fields = ('name', 'description')
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 10, 'cols': 80})},
    }

@admin.register(PricingPlanFeature)
class PricingPlanFeatureAdmin(admin.ModelAdmin):
    list_display = ('name', 'pricing_plan')
    list_filter = ('pricing_plan',)
    search_fields = ('name',)

@admin.register(AdditionalService)
class AdditionalServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'price')
    search_fields = ('name', 'description')
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 10, 'cols': 80})},
    }

@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = ('reference', 'customer_name', 'customer_phone', 'status', 'scheduled_date', 'schedule_time', 'total_amount', 'subscription_request_link', 'created_at')
    list_filter = ('status', 'scheduled_date', 'city', 'state', 'vehicle_type')
    search_fields = ('reference', 'customer_name', 'customer_email', 'customer_phone', 'address')
    readonly_fields = ('created_at', 'updated_at', 'reference', 'subscription_request_link')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Customer Information', {
            'fields': ('user', 'customer_name', 'customer_email', 'customer_phone')
        }),
        ('Address Information', {
            'fields': ('address', 'city', 'state', 'postal_code', 'latitude', 'longitude')
        }),
        ('Vehicle Information', {
            'fields': ('vehicle_type', 'manufacturer', 'vehicle_model')
        }),
        ('Booking Details', {
            'fields': ('reference', 'status', 'scheduled_date', 'schedule_time', 'total_amount', 'distance_fee')
        }),
        ('Subscription Information', {
            'fields': ('subscription_request_link',),
            'classes': ('collapse',)
        }),
        ('Additional Information', {
            'fields': ('notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        # Order by created_at descending to show newest requests first
        return super().get_queryset(request).order_by('-created_at')
    
    def service_count(self, obj):
        return obj.services.count()
    service_count.short_description = 'Number of Services'
    
    def subscription_request_link(self, obj):
        if hasattr(obj, 'subscription_request') and obj.subscription_request:
            url = reverse('admin:subscription_plan_subscriptionrequest_change', args=[obj.subscription_request.id])
            return format_html('<a href="{}">View Subscription Request #{}</a>', url, obj.subscription_request.id)
        return "No linked subscription request"
    subscription_request_link.short_description = 'Subscription Request'
    
    filter_horizontal = ('services',)

@admin.register(ServiceRequestResponse)
class ServiceRequestResponseAdmin(admin.ModelAdmin):
    list_display = ('service_request', 'field_staff', 'accepted', 'estimated_arrival_time')
    list_filter = ('accepted', 'field_staff')
    
@admin.register(LiveLocation)
class LiveLocationAdmin(admin.ModelAdmin):
    list_display = ('field_staff', 'service_request', 'latitude', 'longitude', 'timestamp')
    list_filter = ('field_staff', 'timestamp')
    date_hierarchy = 'timestamp'

@admin.register(FieldStaff)
class FieldStaffAdmin(admin.ModelAdmin):
    list_display = ('get_username', 'get_email', 'get_phone')
    search_fields = ('user__username', 'user__email')

    def get_username(self, obj):
        return obj.user.username if obj.user else "-"
    get_username.short_description = 'Username'

    def get_email(self, obj):
        return obj.user.email if obj.user else "-"
    get_email.short_description = 'Email'

    def get_phone(self, obj):
        return obj.user.profile.phone if hasattr(obj.user, 'profile') else "-"
    get_phone.short_description = 'Phone'









