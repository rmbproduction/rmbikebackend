from django.urls import path
from . import views

app_name = 'admin_panel'

urlpatterns = [
    path('', views.admin_dashboard, name='dashboard'),
    path('analytics/services/', views.service_analytics, name='service_analytics'),
    path('analytics/subscriptions/', views.subscription_analytics, name='subscription_analytics'),
] 