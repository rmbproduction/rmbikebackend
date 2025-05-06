from django.contrib import admin
from django.core.mail import send_mail
from django.conf import settings
from django.utils.html import format_html
from django.urls import reverse
from django.http import HttpResponseRedirect
from .models import User, UserProfile, EmailVerificationToken, ContactMessage

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('get_email', 'name', 'get_username', 'city', 'state', 'country', 'phone')
    search_fields = ('user__email', 'name', 'user__username', 'phone')
    list_filter = ('country', 'state')
    readonly_fields = ('get_email',)

    fieldsets = (
        ('Personal Information', {
            'fields': ('user', 'name', 'phone', 'profile_photo')
        }),
        ('Address Information', {
            'fields': ('address', 'city', 'state', 'country', 'postal_code')
        }),
        ('Vehicle Information', {
            'fields': ('vehicle_name', 'vehicle_type', 'manufacturer')
        }),
    )

    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = 'Email'
    get_email.admin_order_field = 'user__email'

    def get_username(self, obj):
        return obj.user.username
    get_username.short_description = 'Username'
    get_username.admin_order_field = 'user__username'

# Register User model
admin.site.register(User)

# Register EmailVerificationToken with custom admin class
@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'token', 'created_at')
    search_fields = ('user__email', 'token')
    list_filter = ('created_at',)

# Register ContactMessage with custom admin class
@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'status', 'created_at', 'has_response')
    list_filter = ('status', 'created_at')
    search_fields = ('name', 'email', 'phone', 'message')
    readonly_fields = ('created_at', 'updated_at', 'send_response')
    actions = ['mark_as_in_progress', 'mark_as_responded', 'mark_as_closed']
    
    fieldsets = (
        ('Contact Information', {
            'fields': ('name', 'email', 'phone', 'user')
        }),
        ('Message Details', {
            'fields': ('message', 'status')
        }),
        ('Response', {
            'fields': ('response', 'send_response'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def has_response(self, obj):
        """Check if message has a response"""
        if obj.response and obj.response.strip():
            return True
        return False
    has_response.boolean = True
    has_response.short_description = 'Responded'
    
    def send_response(self, obj):
        """Button to send response email"""
        if not obj.id:
            return '-'
            
        if not obj.response or not obj.response.strip():
            return 'Save a response first to enable sending'
            
        if obj.status == 'responded' or obj.status == 'closed':
            return 'Response already sent'
            
        url = reverse('admin:send_response', args=[obj.pk])
        return format_html(
            '<a class="button" href="{}">Send Response Email</a>',
            url
        )
    send_response.short_description = 'Send Response'
    
    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path(
                r'<path:object_id>/send_response/',
                self.admin_site.admin_view(self.send_response_view),
                name='send_response',
            ),
        ]
        return custom_urls + urls
    
    def send_response_view(self, request, object_id):
        """Handle sending response email"""
        try:
            message = self.get_object(request, object_id)
            if not message.response or not message.response.strip():
                self.message_user(request, 'Unable to send: No response text provided', level='error')
                return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
                
            # Send response email
            try:
                send_mail(
                    subject=f'RE: Your inquiry with Repair My Bike - {message.created_at.strftime("%d-%m-%Y")}',
                    message=f'''Dear {message.name},

{message.response}

If you have any further questions, please don't hesitate to contact us.

Best regards,
The Repair My Bike Team
+91 816 812 1711
support@repairmybike.in''',
                    from_email=settings.SUPPORT_FROM_EMAIL,
                    recipient_list=[message.email],
                )
                
                # Update status
                message.status = 'responded'
                message.save()
                
                self.message_user(request, 'Response email sent successfully!')
            except Exception as e:
                self.message_user(request, f'Error sending email: {str(e)}', level='error')
                
        except self.model.DoesNotExist:
            self.message_user(request, 'Contact message not found', level='error')
            
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
    
    def mark_as_in_progress(self, request, queryset):
        queryset.update(status='in_progress')
    mark_as_in_progress.short_description = 'Mark selected as In Progress'
    
    def mark_as_responded(self, request, queryset):
        queryset.update(status='responded')
    mark_as_responded.short_description = 'Mark selected as Responded'
    
    def mark_as_closed(self, request, queryset):
        queryset.update(status='closed')
    mark_as_closed.short_description = 'Mark selected as Closed'
    
    def has_add_permission(self, request):
        # Prevent adding contact messages directly through admin
        return False