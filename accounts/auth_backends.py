from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q
import logging

logger = logging.getLogger(__name__)

User = get_user_model()

class EmailBackend(ModelBackend):
    """
    Custom authentication backend that allows login with email
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            # Since USERNAME_FIELD is 'email', username parameter contains email
            user = User.objects.get(email=username)
            
            # Log authentication attempt
            logger.info(f"Authentication attempt for email: {username}")
            
            # Verify password
            if user.check_password(password):
                # Check if user is active and verified
                if not user.is_active:
                    logger.warning(f"Authentication failed: User {username} is not active")
                    return None
                    
                if not user.email_verified:
                    logger.warning(f"Authentication failed: User {username} email not verified")
                    return None
                
                logger.info(f"Authentication successful for user: {username}")
                return user
            else:
                logger.warning(f"Authentication failed: Invalid password for user {username}")
                return None
                    
        except User.DoesNotExist:
            logger.warning(f"Authentication failed: No user found with email {username}")
            return None
            
    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            logger.warning(f"User retrieval failed: No user found with id {user_id}")
            return None 