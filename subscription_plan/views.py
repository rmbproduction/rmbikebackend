from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets, permissions, status, generics, filters
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from datetime import datetime, timedelta
from .models import Plan, PlanVariant, SubscriptionRequest, UserSubscription, VisitSchedule
from .serializers import (
    PlanSerializer, PlanVariantSerializer, SubscriptionRequestSerializer,
    UserSubscriptionSerializer, VisitScheduleSerializer, 
    VisitCompletionSerializer, VisitCancellationSerializer,
    PreferredDateSerializer
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
            subscription_request.service_request.status = ServiceRequest.STATUS_CONFIRMED
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
        Get all current active subscriptions for the authenticated user
        """
        user = request.user
        current_time = timezone.now()
        
        # Debug timezone information
        print(f"Server time: {current_time}")
        print(f"Server timezone: {current_time.tzinfo}")
        
        subscriptions = UserSubscription.objects.filter(
            user=user,
            status=UserSubscription.ACTIVE,
            start_date__lte=current_time,  # Start date is in the past or now
            end_date__gt=current_time      # End date is in the future
        ).order_by('-start_date')  # Order by most recent first
        
        # Debug subscription information
        for sub in subscriptions:
            print(f"Subscription {sub.id}:")
            print(f"- Start date: {sub.start_date} ({sub.start_date.tzinfo})")
            print(f"- End date: {sub.end_date} ({sub.end_date.tzinfo})")
            print(f"- Current time: {current_time} ({current_time.tzinfo})")
            print(f"- Is start_date <= current_time: {sub.start_date <= current_time}")
            print(f"- Is end_date > current_time: {sub.end_date > current_time}")
        
        if not subscriptions.exists():
            return Response({
                "detail": "You don't have any active subscriptions.",
                "debug_info": {
                    "current_time": str(current_time),
                    "timezone": str(current_time.tzinfo)
                }
            }, status=status.HTTP_404_NOT_FOUND)
            
        serializer = self.get_serializer(subscriptions, many=True)
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
        """
        Check if visit can be created before saving
        """
        subscription = serializer.validated_data.get('subscription')
        
        # Check if subscription is active
        if not subscription.is_active:
            raise serializers.ValidationError("Subscription is not active")
        
        # Check if there are remaining visits
        if subscription.remaining_visits <= 0:
            raise serializers.ValidationError("No remaining visits in subscription")
        
        # Check if user already has a scheduled visit for this date
        scheduled_date = serializer.validated_data.get('scheduled_date')
        existing_visit = VisitSchedule.objects.filter(
            subscription=subscription,
            scheduled_date=scheduled_date,
            status=VisitSchedule.SCHEDULED
        ).exists()
        
        if existing_visit:
            raise serializers.ValidationError("Already have a visit scheduled for this date")
        
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
    
    @action(detail=True, methods=['put'])
    def update_schedule(self, request, pk=None):
        """
        Update a scheduled visit's date and time
        """
        visit = self.get_object()
        serializer = PreferredDateSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Check if visit can be updated
        if visit.status != VisitSchedule.SCHEDULED:
            return Response(
                {"detail": "Only scheduled visits can be updated."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if the user owns this visit's subscription
        if visit.subscription.user != request.user:
            return Response(
                {"detail": "You do not have permission to update this visit."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get validated data
        new_datetime = serializer.validated_data['scheduled_datetime']
        notes = serializer.validated_data.get('notes', visit.service_notes)

        # Update the visit
        visit.scheduled_date = new_datetime
        visit.service_notes = notes
        visit.save()

        response_serializer = self.get_serializer(visit)
        return Response(response_serializer.data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """
        Cancel a scheduled visit and make the slot available again
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
        
        # Get the subscription and update remaining visits
        subscription = visit.subscription
        subscription.remaining_visits += 1  # Restore the visit count
        subscription.save()
        
        cancellation_notes = serializer.validated_data.get('cancellation_notes', None)
        visit.cancel(cancellation_notes)
        
        response_serializer = self.get_serializer(visit)
        return Response({
            "detail": "Visit cancelled successfully. You can schedule a new visit.",
            "visit": response_serializer.data,
            "subscription": UserSubscriptionSerializer(subscription).data
        })
    
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

    @action(detail=False, methods=['get'])
    def check_availability(self, request):
        """
        Check if user can schedule a visit
        Allows scheduling for active subscriptions and future subscriptions
        """
        now = timezone.now()
        
        # Get active subscription
        subscription = UserSubscription.objects.filter(
            user=request.user,
            status='ACTIVE',
            start_date__lte=now,  # Subscription has started
            end_date__gt=now,  # Subscription hasn't ended
        ).order_by('-start_date').first()  # Get the most recent active subscription
        
        if not subscription:
            # If no current subscription, check for future subscriptions
            future_subscription = UserSubscription.objects.filter(
                user=request.user,
                status='ACTIVE',
                start_date__gt=now
            ).order_by('start_date').first()
            
            if future_subscription:
                return Response({
                    "can_schedule": False,
                    "reason": f"Your subscription will be active from {future_subscription.start_date.strftime('%Y-%m-%d')}",
                    "subscription": UserSubscriptionSerializer(future_subscription).data
                })
            else:
                return Response({
                    "can_schedule": False,
                    "reason": "No active or upcoming subscription found",
                    "subscription": None
                })

        # Check remaining visits
        if subscription.remaining_visits <= 0:
            return Response({
                "can_schedule": False,
                "reason": "No remaining visits in subscription",
                "subscription": UserSubscriptionSerializer(subscription).data
            })

        # Calculate earliest possible scheduling date
        earliest_schedule_date = max(
            now.date(),  # Can't schedule in the past
            subscription.start_date.date()  # Can't schedule before subscription starts
        )
            
        return Response({
            "can_schedule": True,
            "remaining_visits": subscription.remaining_visits,
            "subscription": UserSubscriptionSerializer(subscription).data,
            "earliest_schedule_date": earliest_schedule_date.isoformat(),
            "latest_schedule_date": subscription.end_date.date().isoformat()
        })

    @action(detail=False, methods=['get'])
    def available_slots(self, request):
        """
        Get available slots for scheduling
        """
        date = request.query_params.get('date')
        if not date:
            return Response(
                {"detail": "Date parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Get all scheduled visits for the date
        scheduled_visits = VisitSchedule.objects.filter(
            scheduled_date=date,
            status=VisitSchedule.SCHEDULED
        ).values_list('scheduled_time', flat=True)
        
        # Define available time slots (example: 9 AM to 5 PM, hourly slots)
        all_slots = [
            f"{hour:02d}:00" for hour in range(9, 17)  # 9 AM to 4 PM
        ]
        
        available_slots = [
            slot for slot in all_slots
            if slot not in scheduled_visits
        ]
        
        return Response({
            "date": date,
            "available_slots": available_slots
        })

    @action(detail=False, methods=['get'])
    def visit_history(self, request):
        """
        Get completed visit history for a subscription
        """
        subscription_id = request.query_params.get('subscription_id')
        
        # If subscription_id is provided, get visits for that subscription
        if subscription_id:
            visits = self.get_queryset().filter(
                subscription_id=subscription_id,
                status=VisitSchedule.COMPLETED
            ).order_by('-completion_date')
        else:
            # Get visits for all active subscriptions of the user
            visits = self.get_queryset().filter(
                subscription__user=request.user,
                status=VisitSchedule.COMPLETED
            ).order_by('-completion_date')
        
        serializer = self.get_serializer(visits, many=True)
        return Response({
            'count': visits.count(),
            'results': serializer.data
        })

    @action(detail=False, methods=['get'])
    def subscription_visit_summary(self, request):
        """
        Get summary of visits for active subscription
        """
        subscription = UserSubscription.objects.filter(
            user=request.user,
            status='ACTIVE',
            end_date__gt=timezone.now()
        ).first()
        
        if not subscription:
            return Response({
                "detail": "No active subscription found"
            }, status=status.HTTP_404_NOT_FOUND)
        
        completed_visits = VisitSchedule.objects.filter(
            subscription=subscription,
            status=VisitSchedule.COMPLETED
        ).order_by('-completion_date')
        
        upcoming_visits = VisitSchedule.objects.filter(
            subscription=subscription,
            status=VisitSchedule.SCHEDULED,
            scheduled_date__gt=timezone.now()
        ).order_by('scheduled_date')
        
        return Response({
            "subscription": UserSubscriptionSerializer(subscription).data,
            "total_visits_allowed": subscription.plan_variant.max_visits,
            "completed_visits_count": completed_visits.count(),
            "remaining_visits": subscription.remaining_visits,
            "last_visit_date": subscription.last_visit_date,
            "recent_completed_visits": self.get_serializer(completed_visits[:3], many=True).data,
            "upcoming_visits": self.get_serializer(upcoming_visits, many=True).data
        })

    @action(detail=False, methods=['post'])
    def schedule_preferred_date(self, request):
        """
        Schedule a visit for user's preferred date and time
        """
        serializer = PreferredDateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Get validated data
        subscription = serializer.validated_data['subscription']
        scheduled_datetime = serializer.validated_data['scheduled_datetime']
        notes = serializer.validated_data.get('notes', '')

        # Verify user owns the subscription
        if subscription.user != request.user:
            return Response(
                {"detail": "You do not have permission to schedule visits for this subscription."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Create the visit
        visit = VisitSchedule.objects.create(
            subscription=subscription,
            scheduled_date=scheduled_datetime,
            service_notes=notes,
            status=VisitSchedule.SCHEDULED
        )

        response_serializer = self.get_serializer(visit)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def available_dates(self, request):
        """
        Get available dates for scheduling in the next 30 days
        """
        # Get the date range (next 30 days)
        start_date = timezone.now().date()
        end_date = start_date + timedelta(days=30)
        
        # Get all scheduled visits in this date range
        scheduled_visits = VisitSchedule.objects.filter(
            scheduled_date__date__range=(start_date, end_date),
            status=VisitSchedule.SCHEDULED
        ).values('scheduled_date__date').distinct()
        
        # Create a list of dates
        date_list = []
        current_date = start_date
        while current_date <= end_date:
            # Check if the date is not fully booked
            visits_on_date = scheduled_visits.filter(scheduled_date__date=current_date).count()
            
            # Assuming maximum 8 visits per day (9 AM to 5 PM, hourly slots)
            if visits_on_date < 8:
                # Don't include weekends
                if current_date.weekday() < 5:  # Monday = 0, Sunday = 6
                    date_list.append({
                        'date': current_date.isoformat(),
                        'available_slots': 8 - visits_on_date
                    })
            
            current_date += timedelta(days=1)
        
        return Response({
            'available_dates': date_list
        })

    @action(detail=False, methods=['get'])
    def available_times(self, request):
        """
        Get available time slots for a specific date
        """
        # First check if user has an active or future subscription
        subscription = UserSubscription.objects.filter(
            user=request.user,
            status='ACTIVE',
            end_date__gt=timezone.now()
        ).order_by('start_date').first()

        if not subscription:
            return Response({
                "detail": "No active or upcoming subscription found. Please subscribe to schedule visits.",
                "subscription_required": True
            }, status=status.HTTP_400_BAD_REQUEST)

        # Get date parameter
        date_str = request.query_params.get('date')
        if not date_str:
            # If no date provided, return today's available times
            selected_date = timezone.now().date()
            date_str = selected_date.isoformat()
        else:
            try:
                selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {"detail": "Invalid date format. Use YYYY-MM-DD"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Validate selected date is within subscription period
        if selected_date < subscription.start_date.date():
            return Response({
                "detail": f"Cannot schedule before subscription start date ({subscription.start_date.date().isoformat()})",
                "earliest_date": subscription.start_date.date().isoformat()
            }, status=status.HTTP_400_BAD_REQUEST)

        if selected_date > subscription.end_date.date():
            return Response({
                "detail": f"Cannot schedule after subscription end date ({subscription.end_date.date().isoformat()})",
                "latest_date": subscription.end_date.date().isoformat()
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check if date is not in the past
        if selected_date < timezone.now().date():
            return Response(
                {"detail": "Cannot schedule visits for past dates"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if it's a weekend
        if selected_date.weekday() >= 5:  # 5 is Saturday, 6 is Sunday
            return Response(
                {"detail": "Cannot schedule visits on weekends"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get all scheduled visits for the date
        scheduled_times = VisitSchedule.objects.filter(
            scheduled_date__date=selected_date,
            status=VisitSchedule.SCHEDULED
        ).values_list('scheduled_date__time', flat=True)

        # Define available time slots (9 AM to 5 PM, hourly slots)
        all_slots = []
        for hour in range(9, 17):  # 9 AM to 4 PM
            slot_time = timezone.datetime.strptime(f"{hour:02d}:00", "%H:%M").time()
            if slot_time not in scheduled_times:
                all_slots.append({
                    'time': slot_time.strftime('%H:%M'),
                    'display_time': slot_time.strftime('%I:%M %p')
                })

        # If no slots available
        if not all_slots:
            return Response({
                "detail": "No available time slots for selected date",
                "date": date_str,
                "available_times": []
            })

        return Response({
            "date": date_str,
            "available_times": all_slots,
            "subscription": {
                "id": subscription.id,
                "remaining_visits": subscription.remaining_visits
            }
        })
