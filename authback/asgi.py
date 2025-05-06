"""
ASGI config for authback project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import path
from repairing_service.consumers import ServiceRequestConsumer, AdminDashboardConsumer

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'authback.settings')

# Get the Django ASGI application
django_asgi_app = get_asgi_application()

# Define WebSocket URL patterns
websocket_urlpatterns = [
    path('ws/service/', ServiceRequestConsumer.as_asgi()),
    path('ws/admin/', AdminDashboardConsumer.as_asgi()),
]

# Configure the ASGI application with protocol routers
application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})
