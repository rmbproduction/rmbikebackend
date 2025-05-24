from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from django.middleware.csrf import get_token

class RoleMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.user.is_authenticated:
            # Instead of setting properties directly on the user object,
            # store role information in request attributes
            
            # Check email for admin status
            if request.user.email == 'admin@repairmybike.in':
                request.is_admin = True
                request.is_staff = True
                request.is_field_staff = False
                request.is_customer = False
            # Check for field staff status
            elif request.user.email.endswith('@field.repairmybike.in'):
                request.is_admin = False
                request.is_staff = False
                request.is_field_staff = True
                request.is_customer = False
            # Check for regular staff status
            elif request.user.email.endswith('@repairmybike.in'):
                request.is_admin = False
                request.is_staff = True
                request.is_field_staff = False
                request.is_customer = False
            # Regular customers
            else:
                request.is_admin = False
                request.is_staff = False
                request.is_field_staff = False
                request.is_customer = True

class CSRFSecureMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Force CSRF cookie to be set with secure flag
        if not request.COOKIES.get('csrftoken'):
            get_token(request)  # This will set the CSRF cookie
            
        response = self.get_response(request)
        
        # Ensure CSRF cookie has correct flags
        if 'csrftoken' in response.cookies:
            response.cookies['csrftoken']['secure'] = True
            response.cookies['csrftoken']['httponly'] = False
            response.cookies['csrftoken']['samesite'] = 'Lax'
            if settings.CSRF_COOKIE_DOMAIN:
                response.cookies['csrftoken']['domain'] = settings.CSRF_COOKIE_DOMAIN
        
        return response