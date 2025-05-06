"""
URL configuration for authback project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.views.generic import RedirectView
from accounts.views import accounts_root_view

urlpatterns = [
    path('', RedirectView.as_view(url='/api/accounts/', permanent=False), name='root'),  # Add this line
    path('admin/', admin.site.urls),
    path('api/accounts/', include('accounts.urls')),
    path('api/vehicle/', include('vehicle.urls')),
    path('api/repairing_service/', include('repairing_service.urls')),
    path('api/marketplace/', include('marketplace.urls')),
    path('api/subscription/', include('subscription_plan.urls')),  # Add subscription plan URLs
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += staticfiles_urlpatterns()
