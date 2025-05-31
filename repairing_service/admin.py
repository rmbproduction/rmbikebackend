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
    list_display = ('reference', 'customer_name', 'customer_phone', 'status', 'purchase_type', 'get_services_display', 'total_amount', 'scheduled_date', 'schedule_time', 'created_at')
    list_filter = ('status', 'purchase_type', 'scheduled_date', 'city', 'state', 'vehicle_type')
    search_fields = ('reference', 'customer_name', 'customer_email', 'customer_phone', 'address')
    readonly_fields = ('created_at', 'updated_at', 'reference', 'get_services_details')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Customer Information', {
            'fields': ('user', 'customer_name', 'customer_email', 'customer_phone')
        }),
        ('Service Details', {
            'fields': ('get_services_details', 'purchase_type', 'total_amount'),
            'classes': ('wide',)
        }),
        ('Address Information', {
            'fields': ('address', 'city', 'state', 'postal_code', 'latitude', 'longitude')
        }),
        ('Vehicle Information', {
            'fields': ('vehicle_type', 'manufacturer', 'vehicle_model')
        }),
        ('Booking Details', {
            'fields': ('reference', 'status', 'scheduled_date', 'schedule_time', 'distance_fee')
        }),
        ('Additional Information', {
            'fields': ('notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).order_by('-created_at')
    
    def get_services_display(self, obj):
        services = obj.services.all()
        if services:
            return ", ".join([f"{s.name}" for s in services])
        return "No services"
    get_services_display.short_description = 'Services'

    def get_services_details(self, obj):
        services = obj.services.all()
        if not services:
            return "No services selected"
            
        html = '<div style="margin-bottom: 10px;"><strong>Selected Services:</strong></div>'
        html += '<table style="width: 100%; border-collapse: collapse;">'
        html += '<tr style="background-color: #f5f5f5;"><th style="padding: 8px; border: 1px solid #ddd;">Service Name</th><th style="padding: 8px; border: 1px solid #ddd;">Category</th><th style="padding: 8px; border: 1px solid #ddd;">Price</th><th style="padding: 8px; border: 1px solid #ddd;">Duration</th></tr>'
        
        for service in services:
            html += f'''
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;">{service.name}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{service.category.name}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">₹{service.base_price}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{service.duration}</td>
                </tr>
            '''
        
        html += '</table>'
        
        if obj.notes:
            html += f'<div style="margin-top: 15px;"><strong>Customer Notes:</strong><br/>{obj.notes}</div>'
            
        return format_html(html)
    get_services_details.short_description = 'Service Details'
    
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









