from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django import forms
import cloudinary
import cloudinary.uploader
from django.contrib import messages
from .models import (
    PartCategory, SparePart, PartReview,
    PartsCart, PartsCartItem, PartsOrder, PartsOrderItem, DistancePricingRule
)

class SparePartAdminForm(forms.ModelForm):
    upload_image = forms.FileField(required=False, label="Upload Main Image")
    
    class Meta:
        model = SparePart
        fields = '__all__'
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Handle image upload
        uploaded_image = self.cleaned_data.get('upload_image')
        if uploaded_image:
            try:
                # Upload to Cloudinary
                result = cloudinary.uploader.upload(
                    uploaded_image,
                    folder=f"spare_parts/{instance.uuid}",
                    public_id=f"{instance.slug}_{instance.uuid}",
                    overwrite=True
                )
                
                # Set the main_image field with the Cloudinary public_id
                instance.main_image = result['public_id']
            except Exception as e:
                self.add_error('upload_image', f"Error uploading to Cloudinary: {str(e)}")
        
        if commit:
            instance.save()
            self.save_m2m()
        
        return instance

class PartCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'parent', 'is_active', 'category_image_preview')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('category_image_preview',)
    
    def category_image_preview(self, obj):
        if obj.image and hasattr(obj.image, 'url'):
            return format_html('<img src="{}" width="100" height="auto" />', obj.image.url)
        return "No Image"
    
    category_image_preview.short_description = 'Image Preview'

class SparePartAdmin(admin.ModelAdmin):
    form = SparePartAdminForm
    list_display = ('name', 'part_number', 'price', 'discounted_price', 'stock_quantity', 'availability_status', 'is_active', 'image_preview')
    list_filter = ('category', 'availability_status', 'is_active', 'is_featured')
    search_fields = ('name', 'part_number', 'description')
    prepopulated_fields = {'slug': ('name',)}
    filter_horizontal = ('manufacturers', 'vehicle_models', 'vehicle_types')
    list_editable = ('price', 'discounted_price', 'stock_quantity', 'availability_status')
    readonly_fields = ('image_preview', 'additional_images_preview')
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'part_number', 'category', 'description', 'features')
        }),
        ('Pricing and Inventory', {
            'fields': ('price', 'discounted_price', 'stock_quantity', 'availability_status')
        }),
        ('Vehicle Compatibility', {
            'fields': ('manufacturers', 'vehicle_models', 'vehicle_types')
        }),
        ('Media', {
            'fields': ('upload_image', 'image_preview', 'additional_images', 'additional_images_preview')
        }),
        ('Specifications', {
            'fields': ('specifications',)
        }),
        ('SEO and Display', {
            'fields': ('meta_title', 'meta_description', 'is_featured', 'is_active')
        }),
    )
    
    def image_preview(self, obj):
        if obj.main_image and hasattr(obj.main_image, 'url'):
            return format_html('<img src="{}" width="200" height="auto" />', obj.main_image.url)
        return "No Main Image"
    
    def additional_images_preview(self, obj):
        if not obj.additional_images:
            return "No Additional Images"
        
        html = '<div style="display: flex; flex-wrap: wrap; gap: 10px;">'
        for img in obj.additional_images:
            if 'url' in img:
                html += f'<img src="{img["url"]}" width="150" height="auto" style="margin: 5px;" />'
        html += '</div>'
        return mark_safe(html)
    
    def save_model(self, request, obj, form, change):
        """Override save_model to ensure the image is properly saved"""
        super().save_model(request, obj, form, change)
        
        # Check if we need to update the image preview after save
        if obj.main_image and hasattr(obj.main_image, 'url'):
            # Force refresh the admin page to show the new image
            request._messages.add(
                messages.INFO, 
                f"Image uploaded successfully. URL: {obj.main_image.url}"
            )
    
    image_preview.short_description = 'Main Image Preview'
    additional_images_preview.short_description = 'Additional Images Preview'

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
