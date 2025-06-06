# # accounts/utils.py
# def jwt_payload_handler(user):
#     return {
#         'user_id': user.id,
#         'username': user.username,
#         'email': user.email,
#         'exp': datetime.datetime.utcnow() + settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME']
#     }

from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def send_verification_email(to_email, verification_url):
    """
    Send verification email to user
    """
    try:
        subject = "Verify Your Email - Repair My Bike"
        message = f"""Thank you for signing up with Repair My Bike!

Please click the link below to verify your email address:

{verification_url}

This link will expire in 24 hours.

If you did not create an account, please ignore this email.

Best regards,
The Repair My Bike Team"""

        # Log email settings before sending
        logger.info(f"Sending verification email to: {to_email}")
        logger.info(f"Using SMTP settings: {settings.EMAIL_HOST}:{settings.EMAIL_PORT}")

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            fail_silently=False
        )
        
        logger.info(f"Verification email sent successfully to {to_email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send verification email to {to_email}: {str(e)}")
        logger.error("Error details:", exc_info=True)
        raise