from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PartCategoryViewSet, SparePartViewSet

router = DefaultRouter()
router.register('categories', PartCategoryViewSet)
router.register('parts', SparePartViewSet)

urlpatterns = [
    path('', include(router.urls)),
] 