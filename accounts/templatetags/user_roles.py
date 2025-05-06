from django import template
from django.http import HttpRequest

register = template.Library()

@register.filter
def is_admin(user_or_request):
    """Check if the user is an admin"""
    if isinstance(user_or_request, HttpRequest):
        return getattr(user_or_request, 'is_admin', False)
    return getattr(user_or_request, 'is_admin', False)

@register.filter
def is_staff(user_or_request):
    """Check if the user is staff"""
    if isinstance(user_or_request, HttpRequest):
        return getattr(user_or_request, 'is_staff', False)
    return getattr(user_or_request, 'is_staff', False)

@register.filter
def is_field_staff(user_or_request):
    """Check if the user is field staff"""
    if isinstance(user_or_request, HttpRequest):
        return getattr(user_or_request, 'is_field_staff', False)
    return getattr(user_or_request, 'is_field_staff', False)

@register.filter
def is_customer(user_or_request):
    """Check if the user is a customer"""
    if isinstance(user_or_request, HttpRequest):
        return getattr(user_or_request, 'is_customer', False)
    return getattr(user_or_request, 'is_customer', False) 