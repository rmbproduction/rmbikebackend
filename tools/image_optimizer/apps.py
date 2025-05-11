from django.apps import AppConfig


class ImageOptimizerConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tools.image_optimizer"
    verbose_name = "Image Optimizer"

    def ready(self):
        # Import signal handlers when app is ready
        import tools.image_optimizer.signals 