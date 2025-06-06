from django.contrib import admin
from .models import SparePart, PartCategory, PartReview

# Register the models
admin.site.register(PartCategory)
admin.site.register(SparePart)
admin.site.register(PartReview)

# # Admin customization classes
# class PartCategoryAdmin(admin.ModelAdmin):
#     list_display = ('name', 'parent', 'is_active', 'created_at')
#     list_filter = ('is_active', 'parent', 'created_at')
#     search_fields = ('name', 'description')
#     prepopulated_fields = {'slug': ('name',)}
#     readonly_fields = ('created_at', 'updated_at')
#     ordering = ('name',)

# class SparePartAdmin(admin.ModelAdmin):
#     list_display = ('name', 'part_number', 'category', 'price', 'stock_quantity', 'availability_status', 'is_active')
#     list_filter = (
#         'category',
#         'availability_status',
#         'is_active',
#         'is_featured',
#         'manufacturers',
#         'vehicle_types'
#     )
#     search_fields = ('name', 'part_number', 'description')
#     prepopulated_fields = {'slug': ('name',)}
#     readonly_fields = ('created_at', 'updated_at')
#     filter_horizontal = ('manufacturers', 'vehicle_models', 'vehicle_types')
    
#     fieldsets = (
#         ('Basic Information', {
#             'fields': ('name', 'slug', 'part_number', 'category', 'description', 'features')
#         }),
#         ('Pricing & Inventory', {
#             'fields': ('price', 'discounted_price', 'stock_quantity', 'availability_status')
#         }),
#         ('Vehicle Compatibility', {
#             'fields': ('manufacturers', 'vehicle_models', 'vehicle_types')
#         }),
#         ('Media', {
#             'fields': ('main_image', 'additional_images')
#         }),
#         ('SEO & Display', {
#             'fields': ('meta_title', 'meta_description', 'is_featured', 'is_active')
#         }),
#         ('Specifications', {
#             'fields': ('specifications',)
#         }),
#         ('Timestamps', {
#             'fields': ('created_at', 'updated_at'),
#             'classes': ('collapse',)
#         })
#     )

# class PartReviewAdmin(admin.ModelAdmin):
#     list_display = ('part', 'user', 'rating', 'purchase_verified', 'created_at')
#     list_filter = ('rating', 'purchase_verified', 'created_at')
#     search_fields = ('part__name', 'user__username', 'review_text')
#     readonly_fields = ('created_at', 'updated_at')
#     raw_id_fields = ('part', 'user')

# # Register the models with their admin classes
