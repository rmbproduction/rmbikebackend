def user_roles(request):
    """
    Context processor that adds user role information to the template context.
    """
    context = {}
    
    # Only add role information if user is authenticated
    if hasattr(request, 'user') and request.user.is_authenticated:
        # Get roles from request attributes set by RoleMiddleware
        context['is_admin'] = getattr(request, 'is_admin', request.user.is_admin)
        context['is_staff'] = getattr(request, 'is_staff', request.user.is_staff)
        context['is_field_staff'] = getattr(request, 'is_field_staff', request.user.is_field_staff)
        context['is_customer'] = getattr(request, 'is_customer', request.user.is_customer)
    
    return context 