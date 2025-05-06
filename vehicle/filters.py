import django_filters
from .models import VehicleModel

class VehicleModelFilter(django_filters.FilterSet):
    manufacturer = django_filters.NumberFilter(field_name='manufacturer__id')
    vehicle_type = django_filters.NumberFilter(field_name='vehicle_type__id')
    
    class Meta:
        model = VehicleModel
        fields = ['manufacturer', 'vehicle_type']