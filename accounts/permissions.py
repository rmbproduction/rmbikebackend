from rest_framework.permissions import BasePermission

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        # Check request.is_admin first (set by middleware), then fall back to user property
        if hasattr(request, 'is_admin') and request.is_admin:
            return True
            
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.email == 'admin@repairmybike.in'
        )

class IsStaff(BasePermission):
    def has_permission(self, request, view):
        # Check request.is_staff first (set by middleware), then fall back to user property
        if hasattr(request, 'is_staff') and request.is_staff:
            return True
            
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.email.endswith('@repairmybike.in') and
            not request.user.email.endswith('@field.repairmybike.in')
        )

class IsFieldStaff(BasePermission):
    def has_permission(self, request, view):
        # Check request.is_field_staff first (set by middleware), then fall back to user property  
        if hasattr(request, 'is_field_staff') and request.is_field_staff:
            return True
            
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.email.endswith('@field.repairmybike.in')
        )

class IsCustomer(BasePermission):
    def has_permission(self, request, view):
        # Check request.is_customer first (set by middleware), then fall back to user property
        if hasattr(request, 'is_customer') and request.is_customer:
            return True
            
        return bool(
            request.user and
            request.user.is_authenticated and
            not request.user.email.endswith('@repairmybike.in') and
            not request.user.email.endswith('@field.repairmybike.in') and
            request.user.email != 'admin@repairmybike.in'
        )

class IsAdminOrStaffOrFieldStaff(BasePermission):
    def has_permission(self, request, view):
        # Check middleware attributes first, then fall back to user properties
        if (hasattr(request, 'is_admin') and request.is_admin or
            hasattr(request, 'is_staff') and request.is_staff or
            hasattr(request, 'is_field_staff') and request.is_field_staff):
            return True
            
        return bool(
            request.user and
            request.user.is_authenticated and
            (request.user.email == 'admin@repairmybike.in' or 
             request.user.email.endswith('@repairmybike.in'))
        )

class IsAdminOrOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        # Check if admin
        is_admin = False
        if hasattr(request, 'is_admin'):
            is_admin = request.is_admin
        else:
            is_admin = bool(request.user and request.user.is_authenticated and 
                           request.user.email == 'admin@repairmybike.in')
                           
        # Check if owner (adjust as needed based on your object structure)
        return is_admin or obj.owner == request.user


from rest_framework import serializers
from .models import UserProfile

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['email', 'name', 'username', 'address', 'vehicle_name', 'vehicle_type', 'manufacturer']