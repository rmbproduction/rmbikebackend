from django.contrib import admin
from django.utils.html import format_html
from .models import VehicleType, Manufacturer, VehicleModel, UserVehicle, VehicleImage
from accounts.models import UserProfile

# VehicleImageInline for UserVehicle Admin
class VehicleImageInline(admin.TabularInline):
    model = VehicleImage
    extra = 1
    fields = ('image', 'image_preview', 'position', 'is_primary', 'caption')
    readonly_fields = ('image_preview',)
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="150" height="auto" />', obj.preview_url)
        return "No Image"
    image_preview.short_description = 'Preview'

# VehicleType Admin Configuration
class VehicleTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'image_preview')
    search_fields = ('name',)
    list_filter = ('name',)
    readonly_fields = ('image_preview',)
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="150" height="auto" />', obj.image.url)
        return "No Image"
    image_preview.short_description = 'Image Preview'

# Manufacturer Admin Configuration
class ManufacturerAdmin(admin.ModelAdmin):
    list_display = ('name', 'image_preview')
    search_fields = ('name',)
    list_filter = ('name',)
    list_per_page = 10
    readonly_fields = ('image_preview',)
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="150" height="auto" />', obj.image.url)
        return "No Image"
    image_preview.short_description = 'Image Preview'

# VehicleModel Admin Configuration
class VehicleModelAdmin(admin.ModelAdmin):
    list_display = ('name', 'manufacturer', 'vehicle_type', 'image_preview')
    list_filter = ('manufacturer', 'vehicle_type')
    search_fields = ('name', 'manufacturer__name')
    readonly_fields = ('image_preview',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'manufacturer', 'vehicle_type')
        }),
        ('Images', {
            'fields': ('image', 'image_preview'),
            'classes': ('collapse',),
        }),
    )
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="150" height="auto" />', obj.image.url)
        return "No Image"
    image_preview.short_description = 'Image Preview'

# UserVehicle Admin Configuration
class UserVehicleAdmin(admin.ModelAdmin):
    list_display = ('registration_number', 'user', 'manufacturer_name', 'model_name', 'year', 'vehicle_image_preview')
    list_filter = ('manufacturer_name', 'vehicle_type_name')
    search_fields = ('registration_number', 'user__email', 'manufacturer_name', 'model_name')
    raw_id_fields = ('user',)
    readonly_fields = ('vehicle_image_preview',)
    
    fieldsets = (
        ('Owner Information', {
            'fields': ('user', 'registration_number', 'purchase_date')
        }),
        ('Vehicle Details', {
            'fields': ('vehicle_type_name', 'manufacturer_name', 'model_name', 'color', 'year', 'mileage')
        }),
        ('Legacy Image', {
            'fields': ('vehicle_image', 'vehicle_image_preview'),
            'classes': ('collapse',),
        }),
        ('Additional Information', {
            'fields': ('insurance_expiry', 'notes'),
            'classes': ('collapse',),
        }),
    )
    
    inlines = [VehicleImageInline]
    
    def vehicle_image_preview(self, obj):
        if obj.vehicle_image:
            return format_html('<img src="{}" width="150" height="auto" />', obj.vehicle_image.url)
        return "No Image"
    vehicle_image_preview.short_description = 'Image Preview'

# VehicleImage Admin Configuration
class VehicleImageAdmin(admin.ModelAdmin):
    list_display = ('user_vehicle', 'position', 'is_primary', 'upload_date', 'image_preview')
    list_filter = ('position', 'is_primary', 'upload_date')
    search_fields = ('user_vehicle__registration_number', 'caption')
    raw_id_fields = ('user_vehicle',)
    readonly_fields = ('image_preview',)
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="150" height="auto" />', obj.preview_url)
        return "No Image"
    image_preview.short_description = 'Image Preview'

# Register Models with Admin
admin.site.register(VehicleType, VehicleTypeAdmin)
admin.site.register(Manufacturer, ManufacturerAdmin)
admin.site.register(VehicleModel, VehicleModelAdmin)
admin.site.register(UserVehicle, UserVehicleAdmin)
admin.site.register(VehicleImage, VehicleImageAdmin)
