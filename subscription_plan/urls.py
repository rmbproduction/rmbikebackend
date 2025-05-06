from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create a router and register our viewsets with it
router = DefaultRouter()
router.register(r'plans', views.PlanViewSet, basename='plan')
router.register(r'plan-variants', views.PlanVariantViewSet, basename='plan-variant')
router.register(r'subscription-requests', views.SubscriptionRequestViewSet, basename='subscription-request')
router.register(r'subscriptions', views.UserSubscriptionViewSet, basename='subscription')
router.register(r'visits', views.VisitScheduleViewSet, basename='visit')

# The API URLs are now determined automatically by the router
urlpatterns = [
    path('', include(router.urls)),
] 