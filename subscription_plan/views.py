from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets, permissions, status, generics, filters
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from .models import Plan, PlanVariant, SubscriptionRequest, UserSubscription, VisitSchedule
from .serializers import (
    PlanSerializer, PlanVariantSerializer, SubscriptionRequestSerializer,
    UserSubscriptionSerializer, VisitScheduleSerializer, 
    VisitCompletionSerializer, VisitCancellationSerializer
)
from repairing_service.models import ServiceRequest


class PlanViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows plans to be viewed.
    """
    queryset = Plan.objects.filter(is_active=True)
    serializer_class = PlanSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['plan_type']
    search_fields = ['name', 'description']
    
    @action(detail=True, methods=['get'])
    def variants(self, request, pk=None):
        """
        Return all variants for a specific plan
        """
        plan = self.get_object()
        variants = PlanVariant.objects.filter(plan=plan, is_active=True)
        serializer = PlanVariantSerializer(variants, many=True)
        return Response(serializer.data)


class PlanVariantViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows plan variants to be viewed.
    """
    queryset = PlanVariant.objects.filter(is_active=True)
    serializer_class = PlanVariantSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['plan', 'duration_type']


class SubscriptionRequestViewSet(viewsets.ModelViewSet):
    """
    API endpoint for subscription requests 
    """
    serializer_class = SubscriptionRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        # Admin users can see all requests
        if user.is_staff:
            return SubscriptionRequest.objects.all().order_by('-request_date')
        # Regular users can only see their own requests
        return SubscriptionRequest.objects.filter(user=user).order_by('-request_date')
    
    def perform_create(self, serializer):
        """
        When creating a subscription request, automatically set the user to the current user
        """
        serializer.save(user=self.request.user)
    
    def create(self, request, *args, **kwargs):
        """
        Override to ensure user is properly set and correct response formatting
        """
        # Copy request data to make sure we don't modify the original
        data = request.data.copy()
        
        # Add user ID to the data if not present
        if 'user' not in data:
            data['user'] = request.user.id
            
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """
        Get detailed status information about a subscription request
        """
        subscription_request = self.get_object()
        
        # Check if the user is authorized to see this information
        if not request.user.is_staff and subscription_request.user != request.user:
            return Response(
                {"detail": "You do not have permission to view this subscription request."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get the related service request if exists
        service_request_status = None
        service_request_reference = None
        if subscription_request.service_request:
            service_request_status = subscription_request.service_request.status
            service_request_reference = subscription_request.service_request.reference
        
        # Check if there's an active subscription created from this request
        active_subscription = None
        if subscription_request.status == SubscriptionRequest.APPROVED:
            active_subscription = UserSubscription.objects.filter(
                user=subscription_request.user,
                plan_variant=subscription_request.plan_variant,
                status=UserSubscription.ACTIVE
            ).first()
        
        from .serializers import UserSubscriptionSerializer
        subscription_serializer = self.get_serializer(subscription_request)
        active_subscription_serializer = UserSubscriptionSerializer(active_subscription) if active_subscription else None
        
        result = {
            'subscription_request': subscription_serializer.data,
            'service_request_status': service_request_status,
            'service_request_reference': service_request_reference,
            'active_subscription': active_subscription_serializer.data if active_subscription else None
        }
        
        return Response(result)
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def approve(self, request, pk=None):
        """
        Admin action to approve a subscription request and create UserSubscription
        """
        subscription_request = self.get_object()
        admin_notes = request.data.get('admin_notes', None)
        
        if subscription_request.status != SubscriptionRequest.PENDING:
            return Response(
                {"detail": "Only pending requests can be approved."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Calculate subscription duration based on plan variant
        start_date = timezone.now()
        duration_mapping = {
            'QUARTERLY': timezone.timedelta(days=90),  # 3 months
            'HALF_YEARLY': timezone.timedelta(days=180),  # 6 months
            'YEARLY': timezone.timedelta(days=365),  # 1 year
        }
        duration = duration_mapping.get(subscription_request.plan_variant.duration_type)
        end_date = start_date + duration

        # Create UserSubscription
        user_subscription = UserSubscription.objects.create(
            user=subscription_request.user,
            plan_variant=subscription_request.plan_variant,
            start_date=start_date,
            end_date=end_date,
            status='ACTIVE',
            remaining_visits=subscription_request.plan_variant.max_visits,
            last_visit_date=None
        )
        
        # Update subscription request status
        subscription_request.status = SubscriptionRequest.APPROVED
        subscription_request.approval_date = timezone.now()
        subscription_request.admin_notes = admin_notes
        subscription_request.save()

        # Update service request if exists
        if subscription_request.service_request:
            subscription_request.service_request.status = ServiceRequest.STATUS_APPROVED
            subscription_request.service_request.save()
        
        serializer = self.get_serializer(subscription_request)
        return Response({
            'subscription_request': serializer.data,
            'user_subscription': UserSubscriptionSerializer(user_subscription).data
        })
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def reject(self, request, pk=None):
        """
        Admin action to reject a subscription request
        """
        subscription_request = self.get_object()
        reason = request.data.get('reason', 'Rejected by administrator')
        
        if subscription_request.status != SubscriptionRequest.PENDING:
            return Response(
                {"detail": "Only pending requests can be rejected."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Ensure the service_request is updated as well
        subscription_request.reject(reason)
        
        serializer = self.get_serializer(subscription_request)
        return Response(serializer.data)


class UserSubscriptionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for user subscriptions
    """
    serializer_class = UserSubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        # Admin users can see all subscriptions
        if user.is_staff:
            return UserSubscription.objects.all().order_by('-created_at')
        # Regular users can only see their own subscriptions
        return UserSubscription.objects.filter(user=user).order_by('-created_at')
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """
        Action to cancel a subscription
        """
        subscription = self.get_object()
        
        # Check if the user owns this subscription or is an admin
        if not request.user.is_staff and subscription.user != request.user:
            return Response(
                {"detail": "You do not have permission to cancel this subscription."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if subscription.status != UserSubscription.ACTIVE:
            return Response(
                {"detail": "Only active subscriptions can be cancelled."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        subscription.cancel()
        serializer = self.get_serializer(subscription)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """
        Get the current active subscription for the authenticated user
        """
        user = request.user
        subscription = UserSubscription.objects.filter(
            user=user,
            status=UserSubscription.ACTIVE,
            end_date__gt=timezone.now()
        ).first()
        
        if not subscription:
            return Response(
                {"detail": "You don't have an active subscription."},
                status=status.HTTP_404_NOT_FOUND
            )
            
        serializer = self.get_serializer(subscription)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def profile_subscriptions(self, request):
        """
        Get all subscription information for the user's profile page
        Including:
        - Active and past subscriptions
        - Pending, approved, and rejected subscription requests
        """
        user = request.user
        
        # Get all user subscriptions
        subscriptions = UserSubscription.objects.filter(user=user).order_by('-created_at')
        subscription_serializer = self.get_serializer(subscriptions, many=True)
        
        # Get all subscription requests
        from .serializers import SubscriptionRequestSerializer
        subscription_requests = SubscriptionRequest.objects.filter(user=user).order_by('-request_date')
        request_serializer = SubscriptionRequestSerializer(subscription_requests, many=True)
        
        # Count upcoming scheduled visits
        upcoming_visits_count = VisitSchedule.objects.filter(
            subscription__user=user,
            status=VisitSchedule.SCHEDULED,
            scheduled_date__gt=timezone.now()
        ).count()
        
        return Response({
            'subscriptions': subscription_serializer.data,
            'subscription_requests': request_serializer.data,
            'upcoming_visits_count': upcoming_visits_count,
            'has_active_subscription': subscriptions.filter(
                status=UserSubscription.ACTIVE,
                end_date__gt=timezone.now()
            ).exists()
        })


class VisitScheduleViewSet(viewsets.ModelViewSet):
    """
    API endpoint for scheduling service visits
    """
    serializer_class = VisitScheduleSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        # Admin users can see all visits
        if user.is_staff:
            return VisitSchedule.objects.all().order_by('-scheduled_date')
        # Regular users can only see visits for their subscriptions
        return VisitSchedule.objects.filter(
            subscription__user=user
        ).order_by('-scheduled_date')
    
    def perform_create(self, serializer):
        # Ensure the subscription belongs to the user
        subscription = serializer.validated_data.get('subscription')
        if not self.request.user.is_staff and subscription.user != self.request.user:
            raise permissions.PermissionDenied(
                "You can only schedule visits for your own subscriptions."
            )
        serializer.save()
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def complete(self, request, pk=None):
        """
        Mark a visit as completed and update subscription's remaining visits
        """
        visit = self.get_object()
        serializer = VisitCompletionSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        if visit.status != VisitSchedule.SCHEDULED:
            return Response(
                {"detail": "Only scheduled visits can be marked as completed."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update subscription's remaining visits and last visit date
        subscription = visit.subscription
        if subscription.remaining_visits > 0:
            subscription.remaining_visits -= 1
            subscription.last_visit_date = timezone.now()
            subscription.save()
        else:
            return Response(
                {"detail": "No remaining visits in the subscription."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Complete the visit
        visit.status = VisitSchedule.COMPLETED
        visit.completion_date = timezone.now()
        visit.technician_notes = serializer.validated_data.get('technician_notes')
        visit.save()
        
        response_serializer = self.get_serializer(visit)
        return Response({
            'visit': response_serializer.data,
            'subscription': UserSubscriptionSerializer(subscription).data
        })
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """
        Cancel a scheduled visit
        """
        visit = self.get_object()
        serializer = VisitCancellationSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if the user owns this visit's subscription or is an admin
        if not request.user.is_staff and visit.subscription.user != request.user:
            return Response(
                {"detail": "You do not have permission to cancel this visit."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if visit.status != VisitSchedule.SCHEDULED:
            return Response(
                {"detail": "Only scheduled visits can be cancelled."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        cancellation_notes = serializer.validated_data.get('cancellation_notes', None)
        visit.cancel(cancellation_notes)
        response_serializer = self.get_serializer(visit)
        return Response(response_serializer.data)
    
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """
        Get upcoming visits for the current user
        """
        user = request.user
        visits = VisitSchedule.objects.filter(
            subscription__user=user,
            status=VisitSchedule.SCHEDULED,
            scheduled_date__gt=timezone.now()
        ).order_by('scheduled_date')
        
        serializer = self.get_serializer(visits, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def subscription_status(self, request):
        """
        Get subscription status with remaining visits
        """
        user = request.user
        subscription = UserSubscription.objects.filter(
            user=user,
            status=UserSubscription.ACTIVE,
            end_date__gt=timezone.now()
        ).first()

        if not subscription:
            return Response(
                {"detail": "No active subscription found."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = UserSubscriptionSerializer(subscription)
        return Response({
            'subscription': serializer.data,
            'remaining_visits': subscription.remaining_visits,
            'last_visit_date': subscription.last_visit_date,
            'subscription_valid_until': subscription.end_date
        })

    @action(detail=False, methods=['get'])
    def search(self, request):
        """
        Search visits by date range and status
        """
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        status = request.query_params.get('status')
        
        queryset = self.get_queryset()
        
        if start_date:
            queryset = queryset.filter(scheduled_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(scheduled_date__lte=end_date)
        if status:
            queryset = queryset.filter(status=status)
            
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'results': serializer.data
        })

    @action(detail=False, methods=['get'])
    def by_subscription(self, request):
        """
        Get all visits for a specific subscription
        """
        subscription_id = request.query_params.get('subscription_id')
        if not subscription_id:
            return Response(
                {"detail": "subscription_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        queryset = self.get_queryset().filter(subscription_id=subscription_id)
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'results': serializer.data
        })
