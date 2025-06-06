import os
import requests
import logging
from django.shortcuts import redirect
from django.contrib.auth import authenticate, login
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics, permissions
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.renderers import JSONRenderer, BrowsableAPIRenderer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import TokenError
from django.contrib.auth import get_user_model
from django.conf import settings
from decouple import config 
from django.utils.crypto import get_random_string
from django.core.cache import cache
from django.core.mail import send_mail
from django.urls import reverse
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from django.core.exceptions import ValidationError
from django.utils import timezone
from collections import defaultdict
from datetime import datetime, timedelta
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import jwt
from .models import User, EmailVerificationToken, UserProfile, ContactMessage
from .serializers import (
    UserSerializer, 
    LoginSerializer, 
    LogoutSerializer, 
    PasswordResetSerializer, 
    PasswordResetConfirmSerializer,
    UserProfileSerializer,
    ContactMessageSerializer,
    get_tokens_for_user,
    UserProfileWriteSerializer,
    UserSignupSerializer
)
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db.models import Q
from vehicle.models import VehicleModel, VehicleType, Manufacturer
import json

logger = logging.getLogger(__name__)

# Google OAuth settings
GOOGLE_CLIENT_ID = config("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = config("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = "http://localhost:8000/api/accounts/google/callback/"

# Simple rate limiting
request_counts = defaultdict(list)

def check_rate_limit(ip, limit=5, window=60):
    """
    Check if the IP has exceeded the rate limit.
    limit: maximum number of requests
    window: time window in seconds
    """
    now = datetime.now()
    request_times = request_counts[ip]
    
    # Remove old requests
    request_times = [time for time in request_times if (now - time).total_seconds() < window]
    request_counts[ip] = request_times
    
    # Check if limit is exceeded
    if len(request_times) >= limit:
        return True
    
    # Add current request
    request_times.append(now)
    return False

def validate_password_strength(password):
    """Validate password strength"""
    if len(password) < 8:
        raise ValidationError("Password must be at least 8 characters long")
    if not any(c.isupper() for c in password):
        raise ValidationError("Password must contain at least one uppercase letter")
    if not any(c.islower() for c in password):
        raise ValidationError("Password must contain at least one lowercase letter")
    if not any(c.isdigit() for c in password):
        raise ValidationError("Password must contain at least one number")
    if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password):
        raise ValidationError("Password must contain at least one special character")

def check_login_attempts(email):
    """Check and manage login attempts"""
    attempts = cache.get(f'login_attempts_{email}', 0)
    if attempts >= 5:
        lockout_time = cache.get(f'account_lockout_{email}')
        if (lockout_time):
            remaining_time = (lockout_time - timezone.now()).total_seconds()
            if remaining_time > 0:
                raise ValidationError(f"Account locked. Please try again in {int(remaining_time/60)} minutes.")
            else:
                cache.delete(f'account_lockout_{email}')
                cache.delete(f'login_attempts_{email}')
        else:
            cache.set(f'account_lockout_{email}', timezone.now() + timezone.timedelta(minutes=30), timeout=1800)
            raise ValidationError("Account locked for 30 minutes due to too many failed attempts.")

class PasswordResetView(generics.GenericAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = PasswordResetSerializer
    renderer_classes = [JSONRenderer, BrowsableAPIRenderer]

    @method_decorator(ratelimit(key='ip', rate='3/h', method=['POST']))
    def post(self, request):
        if getattr(request, 'limited', False):
            return Response({
                "error": "Too many password reset attempts. Please try again later.",
                "detail": "Rate limit exceeded"
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        email = serializer.validated_data['email']
        
        # Check rate limiting for reset attempts
        reset_attempts = cache.get(f'reset_attempts_{email}', 0)
        if reset_attempts >= 3:
            return Response({
                "message": "Too many reset attempts. Please try again later."
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)

        try:
            user = User.objects.get(email=email)
            # Generate reset token
            token = get_random_string(64)
            cache.set(f'password_reset_{token}', user.pk, timeout=3600)  # 1 hour expiry

            # Get the environment
            environment = os.environ.get('ENVIRONMENT', 'development')
            
            # Generate reset URL
            # For production, always use the production domain
            if environment == 'production':
                frontend_url = 'https://repairmybike.in'
            else:
                # For development, use the origin header from the request if available
                origin = request.headers.get('Origin')
                if origin and 'localhost' in origin:
                    # Use the origin as frontend URL if it contains localhost
                    frontend_url = origin
                else:
                    # Extract domain from referer header if available
                    referer = request.headers.get('Referer')
                    if referer:
                        # Extract domain from referer (http://domain or https://domain)
                        from urllib.parse import urlparse
                        parsed_uri = urlparse(referer)
                        frontend_url = f"{parsed_uri.scheme}://{parsed_uri.netloc}"
                    else:
                        # Fallback to settings FRONTEND_URL
                        frontend_url = getattr(settings, 'FRONTEND_URL', 'https://repairmybike.in')
            
            # Safety check to prevent localhost URLs in production
            if environment == 'production' and ('localhost' in frontend_url or '127.0.0.1' in frontend_url):
                frontend_url = 'https://repairmybike.in'
                
            reset_url = f"{frontend_url}/reset-password/{token}"
            
            # Log the reset URL (without token for security)
            logger.info(f"Generated password reset URL with frontend_url: {frontend_url}")

            # Send reset email
            send_mail(
                subject="Password Reset Request",
                message=f"Click this link to reset your password:\n\n{reset_url}\n\nThis link will expire in 1 hour.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )

            # Increment reset attempts
            cache.set(f'reset_attempts_{email}', reset_attempts + 1, timeout=3600)
            
            # Log the reset request
            logger.info(f"Password reset requested for {email}")

            return Response({
                "message": "Password reset email sent. Please check your email."
            }, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            # Don't reveal if email exists or not
            return Response({
                "message": "If an account exists with this email, you will receive a password reset link."
            }, status=status.HTTP_200_OK)

class PasswordResetConfirmView(generics.GenericAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = PasswordResetConfirmSerializer
    renderer_classes = [JSONRenderer, BrowsableAPIRenderer]

    def post(self, request, token):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_password = serializer.validated_data['password']

        # Validate password strength
        try:
            validate_password_strength(new_password)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Get user from cache
        user_id = cache.get(f'password_reset_{token}')
        if not user_id:
            return Response({"error": "Invalid or expired token"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(pk=user_id)
            
            # Check if password was recently used
            if user.check_password(new_password):
                return Response(
                    {"error": "This password was recently used. Please choose a different one."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            user.set_password(new_password)
            user.save()

            # Delete the token from cache
            cache.delete(f'password_reset_{token}')
            
            # Log the password reset
            logger.info(f"Password reset successful for user {user.email}")

            # Determine the correct frontend URL
            environment = os.environ.get('ENVIRONMENT', 'development')
            
            # For production, always use the production domain
            if environment == 'production':
                frontend_url = 'https://repairmybike.in'
            else:
                # For development, try to determine frontend URL from headers
                referer = request.headers.get('Referer')
                if referer:
                    # Extract domain from referer
                    from urllib.parse import urlparse
                    parsed_uri = urlparse(referer)
                    frontend_url = f"{parsed_uri.scheme}://{parsed_uri.netloc}"
                else:
                    # Fallback to settings FRONTEND_URL
                    frontend_url = getattr(settings, 'FRONTEND_URL', 'https://repairmybike.in')
            
            # Safety check for production
            if environment == 'production' and ('localhost' in frontend_url or '127.0.0.1' in frontend_url):
                frontend_url = 'https://repairmybike.in'
                
            login_url = f"{frontend_url}/login-signup"

            return Response({
                "message": "Password has been reset successfully",
                "redirect_url": login_url
            }, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = LoginSerializer

    @method_decorator(ratelimit(key='ip', rate='5/m', method=['POST']))
    def post(self, request):
        try:
            if getattr(request, 'limited', False):
                return Response({
                    "error": "Too many login attempts. Please try again later.",
                    "detail": "Rate limit exceeded"
                }, status=status.HTTP_429_TOO_MANY_REQUESTS)

            serializer = LoginSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']

            # First check if user exists and is unverified
            try:
                user = User.objects.get(email=email)
                if not user.is_active and not user.email_verified:
                    # Check if verification token exists and is valid
                    token = EmailVerificationToken.objects.filter(user=user).first()
                    if token and (timezone.now() - token.created_at) <= timezone.timedelta(hours=24):
                        return Response({
                            "error": "Please verify your email before logging in",
                            "email_verification_required": True,
                            "verification_token_exists": True,
                            "email": email,
                            "message": "Your account exists but is not verified. Please check your email for the verification link."
                        }, status=status.HTTP_401_UNAUTHORIZED)
                    else:
                        # If no valid token exists, suggest re-registration
                        return Response({
                            "error": "Unverified account with expired verification",
                            "email_verification_required": True,
                            "verification_token_exists": False,
                            "message": "Your previous registration was not completed. Please register again.",
                            "should_register_again": True
                        }, status=status.HTTP_401_UNAUTHORIZED)
            except User.DoesNotExist:
                pass

            # Try to check login attempts
            try:
                check_login_attempts(email)
            except ValidationError as e:
                return Response({"error": str(e)}, status=status.HTTP_429_TOO_MANY_REQUESTS)

            # Authenticate user
            user = authenticate(request, email=email, password=password)
            
            if not user:
                # Increment failed login attempts
                attempts = cache.get(f'login_attempts_{email}', 0)
                cache.set(f'login_attempts_{email}', attempts + 1, timeout=3600)
                
                # Check if user exists but password is wrong
                try:
                    existing_user = User.objects.get(email=email)
                    if existing_user.is_active and existing_user.email_verified:
                        return Response({
                            "error": "Invalid password"
                        }, status=status.HTTP_401_UNAUTHORIZED)
                except User.DoesNotExist:
                    return Response({
                        "error": "No account found with this email"
                    }, status=status.HTTP_401_UNAUTHORIZED)
                
                return Response({
                    "error": "Invalid credentials"
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # Reset login attempts on successful login
            cache.delete(f'login_attempts_{email}')
            cache.delete(f'account_lockout_{email}')
            
            # Get tokens with custom claims
            try:
                tokens = get_tokens_for_user(user)
                is_first_login = user.last_login is None
                
                return Response({
                    "message": "Login successful",
                    "is_first_login": is_first_login,
                    "tokens": tokens,
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email,
                        "email_verified": user.email_verified
                    }
                })
                
            except Exception as e:
                logger.error(f"Error generating tokens: {str(e)}")
                return Response({
                    "error": "Authentication successful but failed to generate tokens. Please try again."
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as e:
            logger.error(f"Unexpected login error: {str(e)}")
            return Response({
                "error": "An unexpected error occurred. Please try again later."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from rest_framework_simplejwt.tokens import RefreshToken
@login_required
def success_page(request):
    user = request.user
    refresh = RefreshToken.for_user(user)
    
    return render(request, 'success.html', {
        'access_token': str(refresh.access_token),
        'refresh_token': str(refresh),
        'user': user,
    })

def rate_limit_view(request, exception):
    """View to handle rate limit exceeded responses"""
    return Response(
        {
            "error": "Rate limit exceeded. Please try again later.",
            "detail": "You have made too many requests. Please wait before trying again."
        },
        status=status.HTTP_429_TOO_MANY_REQUESTS
    )

class GoogleLoginView(APIView):
    permission_classes = (permissions.AllowAny,)
    
    def get(self, request):
        url = (
            f"https://accounts.google.com/o/oauth2/v2/auth?"
            f"client_id={GOOGLE_CLIENT_ID}&"
            f"redirect_uri={GOOGLE_REDIRECT_URI}&"
            f"response_type=code&"
            f"scope=openid%20email%20profile"
        )
        return Response({"auth_url": url})

class GoogleCallbackView(APIView):
    permission_classes = (permissions.AllowAny,)
    
    def get(self, request):
        code = request.GET.get("code")
        if not code:
            return Response({"error": "Authorization code not provided"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Exchange code for tokens
            token_url = "https://oauth2.googleapis.com/token"
            token_data = {
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            }
            token_response = requests.post(token_url, data=token_data)
            token_response.raise_for_status()
            access_token = token_response.json().get("access_token")

            # Get user info from Google
            user_info = requests.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            ).json()

            email = user_info.get("email")
            if not email:
                return Response({"error": "Email not provided by Google"}, status=status.HTTP_400_BAD_REQUEST)

            # Get or create user
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': user_info.get('name', email.split('@')[0]),
                    'is_active': True,
                    'email_verified': True
                }
            )

            if created:
                user.set_unusable_password()
                user.save()

            # Generate JWT tokens
            tokens = get_tokens_for_user(user)
            
            return Response({
                "message": "Login successful",
                "tokens": tokens,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email
                }
            })

        except requests.exceptions.RequestException as e:
            logger.error(f"Google OAuth error: {str(e)}")
            return Response(
                {"error": "Failed to authenticate with Google"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Unexpected error during Google authentication: {str(e)}")
            return Response(
                {"error": "An unexpected error occurred"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class SignUpView(APIView):
    def post(self, request):
        try:
            email = request.data.get('email', '').lower()
            username = request.data.get('username', '')

            # Check if user exists
            existing_user = User.objects.filter(email=email).first()
            
            if existing_user:
                if existing_user.email_verified:
                    return Response({
                        'error': 'A verified user with this email already exists.',
                        'verified': True
                    }, status=status.HTTP_400_BAD_REQUEST)
                else:
                    # User exists but not verified - check if we can resend verification
                    if existing_user.can_request_verification():
                        # Delete old tokens
                        EmailVerificationToken.objects.filter(user=existing_user).delete()
                        
                        # Generate new token and send verification email
                        token = EmailVerificationToken.objects.create(user=existing_user)
                        verification_url = f"{settings.FRONTEND_URL}/verify-email/{token.token}"
                        
                        try:
                            from .utils import send_verification_email
                            send_verification_email(existing_user.email, verification_url)
                            existing_user.increment_verification_attempt()
                            
                            return Response({
                                'message': 'This email is already registered but not verified. A new verification email has been sent.',
                                'email': existing_user.email,
                                'verified': False,
                                'verification_sent': True
                            }, status=status.HTTP_200_OK)
                        except Exception as e:
                            logger.error(f"Failed to send verification email: {str(e)}")
                            return Response({
                                'error': 'Failed to send verification email. Please try again later.',
                                'details': str(e) if settings.DEBUG else None
                            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                    else:
                        # Too many attempts
                        time_to_wait = 60 - ((timezone.now() - existing_user.last_verification_sent).total_seconds() / 60)
                        return Response({
                            'error': f'Too many verification attempts. Please wait {int(time_to_wait)} minutes before requesting another verification email.',
                            'verified': False,
                            'retry_after': int(time_to_wait)
                        }, status=status.HTTP_429_TOO_MANY_REQUESTS)

            # No existing user - proceed with new signup
            serializer = UserSignupSerializer(data=request.data)
            if not serializer.is_valid():
                return Response({
                    'error': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

            user = serializer.save()
            user.is_active = False  # User starts inactive
            user.account_status = 'unverified'
            user.save()

            # Generate and save verification token
            token = EmailVerificationToken.objects.create(user=user)
            
            try:
                # Send verification email
                verification_url = f"{settings.FRONTEND_URL}/verify-email/{token.token}"
                from .utils import send_verification_email
                send_verification_email(user.email, verification_url)
                user.increment_verification_attempt()
                
                return Response({
                    'message': 'Registration successful. Please check your email to verify your account.',
                    'email': user.email,
                    'username': user.username,
                    'status': user.account_status,
                    'verified': False,
                    'verification_sent': True
                }, status=status.HTTP_201_CREATED)

            except Exception as e:
                logger.error(f"Failed to send verification email: {str(e)}")
                return Response({
                    'message': 'Account created but verification email failed to send. Please use the resend verification endpoint.',
                    'email': user.email,
                    'status': user.account_status,
                    'verified': False,
                    'verification_sent': False
                }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            return Response({
                'error': 'Registration failed. Please try again.',
                'details': str(e) if settings.DEBUG else None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ResendVerificationView(APIView):
    def post(self, request):
        try:
            email = request.data.get('email')
            if not email:
                return Response(
                    {'error': 'Email is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            user = User.objects.filter(email=email).first()
            if not user:
                return Response(
                    {'error': 'No account found with this email'},
                    status=status.HTTP_404_NOT_FOUND
                )

            if user.email_verified:
                return Response(
                    {'message': 'Email is already verified'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if not user.can_request_verification():
                time_to_wait = 60 - ((timezone.now() - user.last_verification_sent).total_seconds() / 60)
                return Response({
                    'error': f'Too many verification attempts. Please wait {int(time_to_wait)} minutes before trying again.'
                }, status=status.HTTP_429_TOO_MANY_REQUESTS)

            # Delete any existing tokens
            EmailVerificationToken.objects.filter(user=user).delete()
            
            # Create new token and send email
            token = EmailVerificationToken.objects.create(user=user)
            verification_url = f"{settings.FRONTEND_URL}/verify-email/{token.token}"
            
            send_verification_email(user.email, verification_url)
            user.increment_verification_attempt()

            return Response({
                'message': 'Verification email sent successfully',
                'email': user.email
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Resend verification error: {str(e)}")
            return Response(
                {'error': 'Failed to resend verification email'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class VerifyEmailView(APIView):
    def get(self, request, token):
        try:
            verification_token = EmailVerificationToken.objects.get(token=token)
            
            # Check if token is expired (24 hours)
            if timezone.now() > verification_token.created_at + timezone.timedelta(hours=24):
                verification_token.delete()
                return Response({
                    'error': 'Verification link has expired. Please request a new one.'
                }, status=status.HTTP_400_BAD_REQUEST)

            user = verification_token.user
            user.email_verified = True
            user.is_active = True
            user.account_status = 'active'
            user.save()

            # Clean up used token
            verification_token.delete()

            return Response({
                'message': 'Email verified successfully',
                'email': user.email,
                'status': user.account_status
            }, status=status.HTTP_200_OK)

        except EmailVerificationToken.DoesNotExist:
            return Response({
                'error': 'Invalid verification link'
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Email verification error: {str(e)}")
            return Response({
                'error': 'Verification failed'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class LogoutView(APIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = LogoutSerializer

    def post(self, request):
        try:
            serializer = LogoutSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    serializer.errors,
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            refresh_token = serializer.validated_data['refresh']
            
            # Clean the token
            refresh_token = refresh_token.strip()
            if refresh_token.startswith('Bearer '):
                refresh_token = refresh_token[7:].strip()

            # Blacklist the refresh token
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
                
                # Try to log the logout if user is authenticated
                if request.user.is_authenticated:
                    logger.info(f"User {request.user.email} logged out successfully")
                else:
                    logger.info("User logged out successfully (unauthenticated)")

                return Response(
                    {"message": "Successfully logged out"},
                    status=status.HTTP_200_OK
                )
            except (TokenError, ValueError) as e:
                logger.warning(f"Invalid token during logout: {str(e)}")
                return Response(
                    {"error": "Invalid token. Please provide a valid refresh token."},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Exception as e:
            logger.error(f"Logout error: {str(e)}")
            return Response(
                {"error": "An error occurred during logout"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

def accounts_root_view(request):
    return JsonResponse({"message": "Welcome to the Accounts API!"})

from rest_framework.decorators import api_view, permission_classes

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def profile_view(request):
    """Handle user profile operations"""
    try:
        # Get or create profile
        profile, created = UserProfile.objects.get_or_create(
            user=request.user,
            defaults={
                'name': request.user.get_full_name() or request.user.username,
                'address': ''  # Required field with default empty string
            }
        )
        
        if request.method == 'GET':
            serializer = UserProfileSerializer(profile)
            return Response(serializer.data)
            
        elif request.method == 'POST':
            serializer = UserProfileSerializer(profile, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.exception(f"Error in profile view: {str(e)}")
        return Response(
            {"detail": "Error processing profile request. Please try again later."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    
    def get(self, request):
        """Get user profile"""
        try:
            # Log the request for debugging
            logger.info(f"Profile request received for user: {request.user.email}")
            
            # Get or create profile with minimal fields
            profile, created = UserProfile.objects.get_or_create(
                user=request.user,
                defaults={'name': request.user.get_full_name() or request.user.username}
            )
            
            # Log profile retrieval
            logger.info(f"Profile {'created' if created else 'retrieved'} for user: {request.user.email}")
            
            # Serialize with only the fields we know exist
            serializer = UserProfileSerializer(profile)
            data = serializer.data
            
            # Remove any problematic fields if they exist
            if 'preferredLocation' in data:
                data.pop('preferredLocation')
            if 'preferred_location' in data:
                data.pop('preferred_location')
                
            return Response(data)
            
        except Exception as e:
            # Log the full error with traceback
            logger.exception(f"Error in profile retrieval for user {request.user.email}: {str(e)}")
            return Response(
                {"detail": "Error retrieving profile. Please try again later."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def post(self, request):
        """Create or update user profile"""
        try:
            # Log the request
            logger.info(f"Profile update request received for user: {request.user.email}")
            
            # Get or create profile
            profile, created = UserProfile.objects.get_or_create(user=request.user)
            
            # Clean up request data
            data = request.data.copy()
            if 'preferredLocation' in data:
                data.pop('preferredLocation')
            if 'preferred_location' in data:
                data.pop('preferred_location')
            
            # Handle different content types
            if request.content_type and 'application/json' in request.content_type:
                cleaned_data = data
            else:
                cleaned_data = data
                if 'data' in cleaned_data and isinstance(cleaned_data['data'], str):
                    try:
                        json_data = json.loads(cleaned_data['data'])
                        # Remove problematic fields from JSON data
                        if 'preferredLocation' in json_data:
                            json_data.pop('preferredLocation')
                        if 'preferred_location' in json_data:
                            json_data.pop('preferred_location')
                        # Merge cleaned JSON data
                        for key, value in json_data.items():
                            if key not in cleaned_data:
                                cleaned_data[key] = value
                    except json.JSONDecodeError as e:
                        logger.warning(f"JSON decode error in profile update: {str(e)}")
            
            # Update with cleaned data
            serializer = UserProfileSerializer(profile, data=cleaned_data, partial=True)
            
            if serializer.is_valid():
                profile = serializer.save()
                return Response(
                    UserProfileSerializer(profile).data, 
                    status=status.HTTP_200_OK
                )
            
            logger.warning(f"Profile update validation failed: {serializer.errors}")
            return Response(
                serializer.errors, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            logger.exception(f"Error in profile update for user {request.user.email}: {str(e)}")
            return Response(
                {"detail": "Error updating profile. Please try again later."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def patch(self, request):
        """Partially update user profile"""
        try:
            # Log the request
            logger.info(f"Profile patch request received for user: {request.user.email}")
            
            # Get or create profile
            profile, created = UserProfile.objects.get_or_create(
                user=request.user,
                defaults={'name': request.user.get_full_name() or request.user.username}
            )
            
            # Clean up request data
            data = request.data.copy()
            if 'preferredLocation' in data:
                data.pop('preferredLocation')
            if 'preferred_location' in data:
                data.pop('preferred_location')
            
            # Handle different content types
            if request.content_type and 'application/json' in request.content_type:
                cleaned_data = data
            else:
                cleaned_data = data
                if 'data' in cleaned_data and isinstance(cleaned_data['data'], str):
                    try:
                        json_data = json.loads(cleaned_data['data'])
                        # Remove problematic fields from JSON data
                        if 'preferredLocation' in json_data:
                            json_data.pop('preferredLocation')
                        if 'preferred_location' in json_data:
                            json_data.pop('preferred_location')
                        # Merge cleaned JSON data
                        for key, value in json_data.items():
                            cleaned_data[key] = value
                    except json.JSONDecodeError as e:
                        logger.warning(f"JSON decode error in profile patch: {str(e)}")
            
            # Convert field names if needed
            if 'postalCode' in cleaned_data:
                cleaned_data['postal_code'] = cleaned_data.pop('postalCode')
            
            # Update with cleaned data
            serializer = UserProfileSerializer(profile, data=cleaned_data, partial=True)
            
            if serializer.is_valid():
                updated_profile = serializer.save()
                logger.info(f"Profile patched successfully for user {request.user.email}")
                return Response(
                    UserProfileSerializer(updated_profile).data,
                    status=status.HTTP_200_OK
                )
            
            logger.warning(f"Profile patch validation failed: {serializer.errors}")
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            logger.exception(f"Error in profile patch for user {request.user.email}: {str(e)}")
            return Response(
                {"detail": "Error updating profile. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ContactMessageView(APIView):
    """View for handling contact form submissions"""
    permission_classes = [AllowAny]  # Allow anyone to submit the contact form
    serializer_class = ContactMessageSerializer
    
    @method_decorator(ratelimit(key='ip', rate='10/h', method=['POST']))
    @method_decorator(csrf_exempt)  # Add CSRF exemption for external requests
    def post(self, request):
        """Handle contact form submission"""
        try:
            if getattr(request, 'limited', False):
                return Response({
                    'error': 'Too many contact attempts. Please try again later.',
                    'detail': 'Rate limit exceeded'
                }, status=status.HTTP_429_TOO_MANY_REQUESTS)
                
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():
                # Set user if authenticated
                if request.user.is_authenticated:
                    serializer.save(user=request.user)
                else:
                    serializer.save()
                    
                # Send notification email to site admins
                try:
                    admin_email = getattr(settings, 'ADMIN_EMAIL', 'admin@repairmybike.in')
                    send_mail(
                        subject=f'New Contact Form Submission from {serializer.validated_data["name"]}',
                        message=f'Name: {serializer.validated_data["name"]}\n'
                                f'Email: {serializer.validated_data["email"]}\n'
                                f'Phone: {serializer.validated_data["phone"]}\n\n'
                                f'Message: {serializer.validated_data["message"]}',
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[admin_email],
                        fail_silently=True,
                    )
                except Exception as e:
                    # Just log the error, don't fail the submission
                    logger.error(f'Failed to send contact notification email: {str(e)}')
                    
                # Send confirmation email to user
                try:
                    send_mail(
                        subject='Thank you for contacting Repair My Bike',
                        message=f'''Dear {serializer.validated_data["name"]},

Thank you for reaching out to Repair My Bike! We have received your message and one of our experts will get back to you shortly.

Here's a summary of your inquiry:
------------------------------
Name: {serializer.validated_data["name"]}
Email: {serializer.validated_data["email"]}
Phone: {serializer.validated_data["phone"] or "Not provided"}
Message: {serializer.validated_data["message"]}
------------------------------

Our team typically responds within 24-48 hours during business days. If your matter is urgent, please call us at +91 816 812 1711.

Best regards,
The Repair My Bike Team
support@repairmybike.in
''',
                        from_email=settings.EMAIL_HOST_USER,
                        recipient_list=[serializer.validated_data['email']],
                        fail_silently=True,
                    )
                except Exception as e:
                    # Just log the error, don't fail the submission
                    logger.error(f'Failed to send contact confirmation email: {str(e)}')
                    
                logger.info(f'New contact form submission from {serializer.validated_data["name"]} ({serializer.validated_data["email"]})')
                
                return Response({
                    'message': 'Thank you for your message. We will contact you soon!',
                    'success': True
                }, status=status.HTTP_201_CREATED)
                
            # Return validation errors in a more detailed format
            error_details = {}
            for field, errors in serializer.errors.items():
                error_details[field] = [str(error) for error in errors]
                
            return Response({
                'error': 'Invalid form data',
                'details': error_details
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            logger.error(f'Unexpected error in contact form: {str(e)}')
            return Response({
                'error': 'An unexpected error occurred. Please try again later.',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def get(self, request):
        """Return information about the contact endpoint"""
        return Response({
            'message': 'Contact form API endpoint',
            'instructions': 'Send a POST request with name, email, phone (optional), and message'
        }, status=status.HTTP_200_OK)

class TokenRefreshView(APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        try:
            # Get refresh token from request body
            refresh_token = request.data.get('refresh')
                
            if not refresh_token:
                return Response({
                    "error": "No refresh token provided"
                }, status=status.HTTP_400_BAD_REQUEST)

            try:
                # Validate and refresh token
                refresh = RefreshToken(refresh_token)
                
                # Log refresh attempt
                logger.info("Token refresh attempt", extra={
                    'user_id': refresh.get('user_id'),
                    'old_token_exp': datetime.fromtimestamp(refresh['exp']).isoformat(),
                    'old_token_iat': datetime.fromtimestamp(refresh.get('iat', 0)).isoformat()
                })
                
                # Get new tokens
                access_token = str(refresh.access_token)
                new_refresh_token = str(refresh)

                # Log successful refresh
                logger.info("Token refresh successful", extra={
                    'user_id': refresh.get('user_id'),
                    'new_access_exp': datetime.fromtimestamp(refresh.access_token['exp']).isoformat(),
                    'new_refresh_exp': datetime.fromtimestamp(refresh['exp']).isoformat()
                })

                return Response({
                    "access": access_token,
                    "refresh": new_refresh_token
                })

            except TokenError as e:
                logger.warning("Token refresh failed", extra={
                    'error': str(e)
                })
                return Response({
                    "error": "Invalid or expired refresh token"
                }, status=status.HTTP_401_UNAUTHORIZED)

        except Exception as e:
            logger.error(f"Unexpected error during token refresh: {str(e)}")
            return Response({
                "error": "An unexpected error occurred during token refresh"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)