from django.contrib import admin
from .models import (
    PartCategory, SparePart, PartReview,
    PartsCart, PartsCartItem, PartsOrder, PartsOrderItem, DistancePricingRule
)

class PartCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'parent', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}

class SparePartAdmin(admin.ModelAdmin):
    list_display = ('name', 'part_number', 'price', 'discounted_price', 'stock_quantity', 'availability_status', 'is_active')
    list_filter = ('category', 'availability_status', 'is_active', 'is_featured')
    search_fields = ('name', 'part_number', 'description')
    prepopulated_fields = {'slug': ('name',)}
    filter_horizontal = ('manufacturers', 'vehicle_models', 'vehicle_types')
    list_editable = ('price', 'discounted_price', 'stock_quantity', 'availability_status')

class PartReviewAdmin(admin.ModelAdmin):
    list_display = ('part', 'user', 'rating', 'purchase_verified', 'created_at')
    list_filter = ('rating', 'purchase_verified')
    search_fields = ('part__name', 'user__username', 'review_text')
    readonly_fields = ('created_at', 'updated_at')

class PartsCartItemInline(admin.TabularInline):
    model = PartsCartItem
    extra = 0
    readonly_fields = ('get_total_price',)

class PartsCartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'status', 'total_items', 'total_price', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'user__email')
    inlines = [PartsCartItemInline]
    readonly_fields = ('created_at', 'modified_at', 'total_items', 'total_price')

class PartsOrderItemInline(admin.TabularInline):
    model = PartsOrderItem
    extra = 0
    readonly_fields = ('price', 'total')

class PartsOrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'user', 'status', 'payment_status', 'total_amount', 'final_amount', 'created_at')
    list_filter = ('status', 'payment_status', 'created_at')
    search_fields = ('order_number', 'user__username', 'customer_name', 'customer_email')
    readonly_fields = ('uuid', 'order_number', 'created_at', 'updated_at')
    fieldsets = (
        ('Order Information', {
            'fields': ('uuid', 'order_number', 'status', 'payment_status', 'purchase_type')
        }),
        ('Customer Information', {
            'fields': ('user', 'customer_name', 'customer_email', 'customer_phone')
        }),
        ('Shipping Information', {
            'fields': ('shipping_address', 'shipping_city', 'shipping_state', 'shipping_pincode')
        }),
        ('Order Totals', {
            'fields': ('total_amount', 'shipping_charges', 'tax_amount', 'distance_fee', 'discount_amount', 'final_amount')
        }),
        ('Tracking', {
            'fields': ('tracking_number', 'notes')
        }),
        ('Location', {
            'fields': ('latitude', 'longitude')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    inlines = [PartsOrderItemInline]

class DistancePricingRuleAdmin(admin.ModelAdmin):
    list_display = ('id', 'is_active', 'free_radius_km', 'base_charge', 'per_km_charge', 'max_distance_km')
    list_filter = ('is_active',)
    list_editable = ('is_active', 'free_radius_km', 'base_charge', 'per_km_charge', 'max_distance_km')

# Register models
admin.site.register(PartCategory, PartCategoryAdmin)
admin.site.register(SparePart, SparePartAdmin)
admin.site.register(PartReview, PartReviewAdmin)
admin.site.register(PartsCart, PartsCartAdmin)
admin.site.register(PartsOrder, PartsOrderAdmin)
admin.site.register(DistancePricingRule, DistancePricingRuleAdmin)
