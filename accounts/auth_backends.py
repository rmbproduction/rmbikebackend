from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

User = get_user_model()

class EmailBackend(ModelBackend):
    """
    Custom authentication backend that allows login with either email or username
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        # Try to find user by either email or username
        try:
            user = get_user_model().objects.get(
                Q(username=username) | Q(email=username)
            )
            
            # Verify password
            if user.check_password(password):
                # Check if email verification is required and the user is verified
                if user.email_verified:
                    return user
                    
        except get_user_model().DoesNotExist:
            # No user found with this email/username
            return None
            
        # Invalid credentials
        return None
        
    def get_user(self, user_id):
        try:
            return get_user_model().objects.get(pk=user_id)
        except get_user_model().DoesNotExist:
            return None 