from django.contrib import admin
from .models import Vehicle, SellRequest, InspectionReport, PurchaseOffer, Notification

@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('registration_number', 'vehicle_type', 'brand', 'model', 'year', 'status', 'fuel_type', 'Mileage', 'price', 'expected_price')
    list_filter = ('vehicle_type', 'status', 'fuel_type', 'brand')
    search_fields = ('registration_number', 'brand', 'model')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Basic Information', {
            'fields': ('vehicle_type', 'brand', 'model', 'year', 'registration_number', 'owner')
        }),
        ('Specifications', {
            'fields': ('fuel_type', 'engine_capacity', 'kms_driven', 'Mileage', 'color')
        }),
        ('Sales Information', {
            'fields': ('price', 'expected_price', 'emi_available', 'emi_months')
        }),
        ('Documents & Service', {
            'fields': ('last_service_date', 'insurance_valid_till')
        }),
        ('Status', {
            'fields': ('status', 'created_at', 'updated_at')
        }),
        ('Additional Information', {
            'fields': ('images', 'features', 'highlights'),
            'classes': ('collapse',),
        }),
    )

@admin.register(SellRequest)
class SellRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'vehicle', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__email', 'vehicle__registration_number')
    raw_id_fields = ('user', 'vehicle')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'vehicle', 'status', 'pickup_slot', 'pickup_address', 'contact_number')
        }),
        ('Documents', {
            'fields': (
                'registration_certificate', 
                'insurance_document', 
                'puc_certificate',
                'ownership_transfer',
                'additional_documents',
            ),
            'classes': ('collapse',),
        }),
        ('Vehicle Photos', {
            'fields': (
                'photo_front',
                'photo_back',
                'photo_left', 
                'photo_right',
                'photo_dashboard',
                'photo_odometer',
                'photo_engine',
                'photo_extras',
            ),
            'classes': ('collapse',),
        }),
        ('Status Details', {
            'fields': ('rejection_reason',),
            'classes': ('collapse',),
        }),
    )
    
    actions = ['mark_as_confirmed', 'schedule_inspection', 'mark_as_under_inspection', 'move_to_service_center']
    
    def mark_as_confirmed(self, request, queryset):
        updated = queryset.update(status=SellRequest.Status.CONFIRMED)
        self.message_user(request, f"{updated} sell requests marked as confirmed")
    mark_as_confirmed.short_description = "Mark selected as confirmed by call"
    
    def schedule_inspection(self, request, queryset):
        updated = queryset.update(status=SellRequest.Status.INSPECTION_SCHEDULED)
        self.message_user(request, f"Scheduled inspection for {updated} sell requests")
    schedule_inspection.short_description = "Schedule inspection"
    
    def mark_as_under_inspection(self, request, queryset):
        updated = queryset.update(status=SellRequest.Status.UNDER_INSPECTION)
        self.message_user(request, f"{updated} sell requests marked as under inspection")
    mark_as_under_inspection.short_description = "Mark as under inspection"
    
    def move_to_service_center(self, request, queryset):
        updated = queryset.update(status=SellRequest.Status.SERVICE_CENTER)
        self.message_user(request, f"{updated} sell requests moved to service center")
    move_to_service_center.short_description = "Move to service center"

@admin.register(InspectionReport)
class InspectionReportAdmin(admin.ModelAdmin):
    list_display = ('get_registration', 'inspector', 'overall_rating', 'passed', 'created_at')
    list_filter = ('passed', 'overall_rating')
    search_fields = ('sell_request__vehicle__registration_number',)
    readonly_fields = ('created_at', 'updated_at')

    def get_registration(self, obj):
        return obj.sell_request.vehicle.registration_number
    get_registration.short_description = 'Registration Number'

@admin.register(PurchaseOffer)
class PurchaseOfferAdmin(admin.ModelAdmin):
    list_display = ('get_registration', 'market_value', 'offer_price', 'status', 'counter_offer', 'valid_until')
    list_filter = ('status', 'is_negotiable')
    search_fields = ('sell_request__vehicle__registration_number',)
    readonly_fields = ('created_at', 'updated_at')

    def get_registration(self, obj):
        return obj.sell_request.vehicle.registration_number
    get_registration.short_description = 'Registration Number'
    
    actions = ['mark_as_accepted', 'mark_as_rejected', 'extend_validity']
    
    def mark_as_accepted(self, request, queryset):
        for offer in queryset:
            offer.status = PurchaseOffer.OfferStatus.ACCEPTED
            offer.save()
        self.message_user(request, f"{queryset.count()} offers marked as accepted")
    mark_as_accepted.short_description = "Mark offers as accepted"
    
    def mark_as_rejected(self, request, queryset):
        for offer in queryset:
            offer.status = PurchaseOffer.OfferStatus.REJECTED
            offer.save()
        self.message_user(request, f"{queryset.count()} offers marked as rejected")
    mark_as_rejected.short_description = "Mark offers as rejected"
    
    def extend_validity(self, request, queryset):
        from datetime import timedelta
        from django.utils import timezone
        for offer in queryset:
            offer.valid_until = timezone.now() + timedelta(days=7)
            offer.save()
        self.message_user(request, f"Extended validity for {queryset.count()} offers")
    extend_validity.short_description = "Extend offer validity by 7 days"

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'type', 'title', 'is_read', 'created_at')
    list_filter = ('type', 'is_read', 'created_at')
    search_fields = ('user__email', 'title', 'message')
    readonly_fields = ('created_at',)
    
    actions = ['mark_as_read', 'mark_as_unread']
    
    def mark_as_read(self, request, queryset):
        updated = queryset.update(is_read=True)
        self.message_user(request, f"{updated} notifications marked as read")
    mark_as_read.short_description = "Mark as read"
    
    def mark_as_unread(self, request, queryset):
        updated = queryset.update(is_read=False)
        self.message_user(request, f"{updated} notifications marked as unread")
    mark_as_unread.short_description = "Mark as unread"
