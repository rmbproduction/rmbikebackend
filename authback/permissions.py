from rest_framework import permissions

class IsOwnerOrStaff(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object or staff members to access it.
    """
    def has_object_permission(self, request, view, obj):
        # Staff members can access any object
        if request.user.is_staff:
            return True

        # Check if the object has an owner field
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        # Check if the object has a user field
        elif hasattr(obj, 'user'):
            return obj.user == request.user
        # If no owner/user field exists, deny permission
        return False

    def has_permission(self, request, view):
        # Allow staff to perform any action
        if request.user.is_staff:
            return True
        # For non-staff users, only allow safe methods for list views
        if view.action == 'list':
            return request.method in permissions.SAFE_METHODS
        # For other actions, proceed to has_object_permission
        return True

class IsStaffOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow staff members to edit but allow anyone to view.
    """
    def has_permission(self, request, view):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to staff users.
        return request.user and request.user.is_staff

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to staff users.
        return request.user and request.user.is_staff