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
from cloudinary_patch import setup_cloudinary
from django.http import JsonResponse

# Try to set up Cloudinary explicitly
setup_cloudinary()

def cloudinary_test(request):
    """Test endpoint to check Cloudinary connection"""
    from django.core.files.storage import default_storage
    from cloudinary_patch import setup_cloudinary
    
    # Try to set up Cloudinary again
    success = setup_cloudinary()
    
    return JsonResponse({
        'cloudinary_setup_success': success,
        'current_storage': str(default_storage.__class__),
        'is_cloudinary': 'cloudinary' in str(default_storage.__class__).lower(),
        'media_url': settings.MEDIA_URL,
    })

urlpatterns = [
    path('admin/', admin.site.urls),
    path('jet/', include('jet.urls', 'jet')),
    path('jet/dashboard/', include('jet.dashboard.urls', 'jet-dashboard')),
    path('api/accounts/', include('accounts.urls')),
    path('api/vehicle/', include('vehicle.urls')),
    path('api/repairing-service/', include('repairing_service.urls')),
    path('api/subscription/', include('subscription_plan.urls')),
    path('api/marketplace/', include('marketplace.urls')),
    path('api/spare-parts/', include('spare_parts.urls')),
    path('api/cart/', include('cart.urls')),
    path('test-cloudinary/', cloudinary_test, name='test-cloudinary'),
    path('', RedirectView.as_view(url='/admin/')),
    
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += staticfiles_urlpatterns()
