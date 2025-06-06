from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import PartCategory, SparePart, PartReview
from .serializers import (
    PartCategorySerializer,
    SparePartSerializer,
    SparePartListSerializer,
    PartReviewSerializer
)

class PartCategoryViewSet(viewsets.ModelViewSet):
    queryset = PartCategory.objects.filter(is_active=True)
    serializer_class = PartCategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    lookup_field = 'uuid'
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'description']

    def get_queryset(self):
        queryset = super().get_queryset()
        parent = self.request.query_params.get('parent', None)
        if parent == 'null':
            return queryset.filter(parent__isnull=True)
        elif parent:
            return queryset.filter(parent=parent)
        return queryset

class SparePartViewSet(viewsets.ModelViewSet):
    queryset = SparePart.objects.filter(is_active=True)
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    lookup_field = 'uuid'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        'category': ['exact'],
        'manufacturers': ['exact'],
        'vehicle_models': ['exact'],
        'vehicle_types': ['exact'],
        'price': ['gte', 'lte'],
        'is_featured': ['exact'],
        'availability_status': ['exact']
    }
    search_fields = ['name', 'description', 'part_number']
    ordering_fields = ['price', 'created_at', 'name']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return SparePartListSerializer
        return SparePartSerializer

    @action(detail=True, methods=['post'])
    def add_review(self, request, uuid=None):
        part = self.get_object()
        serializer = PartReviewSerializer(data=request.data)
        
        if serializer.is_valid():
            serializer.save(user=request.user, part=part)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def reviews(self, request, uuid=None):
        part = self.get_object()
        reviews = part.reviews.all().order_by('-created_at')
        serializer = PartReviewSerializer(reviews, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def related(self, request, uuid=None):
        part = self.get_object()
        related_parts = SparePart.objects.filter(
            category=part.category
        ).exclude(
            uuid=part.uuid
        )[:5]
        serializer = SparePartListSerializer(related_parts, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def featured(self, request):
        featured_parts = self.get_queryset().filter(is_featured=True)[:8]
        serializer = SparePartListSerializer(featured_parts, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_vehicle(self, request):
        vehicle_type = request.query_params.get('vehicle_type')
        manufacturer = request.query_params.get('manufacturer')
        model = request.query_params.get('model')
        
        queryset = self.get_queryset()
        
        if vehicle_type:
            queryset = queryset.filter(vehicle_types=vehicle_type)
        if manufacturer:
            queryset = queryset.filter(manufacturers=manufacturer)
        if model:
            queryset = queryset.filter(vehicle_models=model)
            
        serializer = SparePartListSerializer(queryset, many=True)
        return Response(serializer.data) 