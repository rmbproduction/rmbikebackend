from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import SellRequest
from authback.utils import send_status_email

@receiver(post_save, sender=SellRequest)
def notify_seller_on_status_change(sender, instance, created, **kwargs):
    if not created:
        subject = f"Your sell request #{instance.id} is now {instance.status}"
        message = (
            f"Hello {instance.user.first_name},\n"
            f"Your bike sale request (ID: {instance.id}) status has changed to '{instance.status}'.\n"
            "Please log in to your dashboard for details.\n"
            "Thank you,\nAutoRevive Team"
        )
        send_status_email.delay(instance.user.email, subject, message)