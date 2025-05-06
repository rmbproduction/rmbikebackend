from django.contrib import admin
from .models import VehicleType, Manufacturer, VehicleModel, UserVehicle, VehicleImage
from accounts.models import UserProfile

# VehicleImageInline for UserVehicle Admin
class VehicleImageInline(admin.TabularInline):
    model = VehicleImage
    extra = 1
    fields = ('image', 'position', 'is_primary', 'caption')

# VehicleType Admin Configuration
class VehicleTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'image')
    search_fields = ('name',)
    list_filter = ('name',)

# Manufacturer Admin Configuration
class ManufacturerAdmin(admin.ModelAdmin):
    list_display = ('name', 'image')
    search_fields = ('name',)
    list_filter = ('name',)
    list_per_page = 10

# VehicleModel Admin Configuration
class VehicleModelAdmin(admin.ModelAdmin):
    list_display = ('name', 'manufacturer', 'vehicle_type')
    list_filter = ('manufacturer', 'vehicle_type')
    search_fields = ('name', 'manufacturer__name')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'manufacturer', 'vehicle_type', 'description')
        }),
        ('Images', {
            'fields': ('image', 'image_front', 'image_back', 'image_side', 'thumbnail'),
            'classes': ('collapse',),
        }),
        ('Specifications', {
            'fields': ('specs',),
            'classes': ('collapse',),
        }),
    )

# UserVehicle Admin Configuration
class UserVehicleAdmin(admin.ModelAdmin):
    list_display = ('registration_number', 'user', 'manufacturer_name', 'model_name', 'year')
    list_filter = ('manufacturer_name', 'vehicle_type_name')
    search_fields = ('registration_number', 'user__email', 'manufacturer_name', 'model_name')
    raw_id_fields = ('user',)
    
    fieldsets = (
        ('Owner Information', {
            'fields': ('user', 'registration_number', 'purchase_date')
        }),
        ('Vehicle Details', {
            'fields': ('vehicle_type_name', 'manufacturer_name', 'model_name', 'color', 'year', 'mileage')
        }),
        ('Legacy Image', {
            'fields': ('vehicle_image',),
            'classes': ('collapse',),
        }),
        ('Additional Information', {
            'fields': ('insurance_expiry', 'notes'),
            'classes': ('collapse',),
        }),
    )
    
    inlines = [VehicleImageInline]

# VehicleImage Admin Configuration
class VehicleImageAdmin(admin.ModelAdmin):
    list_display = ('user_vehicle', 'position', 'is_primary', 'upload_date')
    list_filter = ('position', 'is_primary', 'upload_date')
    search_fields = ('user_vehicle__registration_number', 'caption')
    raw_id_fields = ('user_vehicle',)

# Register Models with Admin
admin.site.register(VehicleType, VehicleTypeAdmin)
admin.site.register(Manufacturer, ManufacturerAdmin)
admin.site.register(VehicleModel, VehicleModelAdmin)
admin.site.register(UserVehicle, UserVehicleAdmin)
admin.site.register(VehicleImage, VehicleImageAdmin)
