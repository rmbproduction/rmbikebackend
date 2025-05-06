from django.core.mail import send_mail
from celery import shared_task

@shared_task
def send_status_email(user_email: str, subject: str, message: str):
    """Send status update email asynchronously."""
    send_mail(
        subject=subject,
        message=message,
        from_email='no-reply@bikeshop.com',
        recipient_list=[user_email],
        fail_silently=False,
    )