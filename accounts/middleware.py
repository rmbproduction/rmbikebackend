from django.utils.deprecation import MiddlewareMixin

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