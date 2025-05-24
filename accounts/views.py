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
    UserProfileWriteSerializer
)
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db.models import Q
from vehicle.models import VehicleModel, VehicleType, Manufacturer
import json

logger = logging.getLogger(__name__)

# Google OAuth settings
GOOGLE_CLIENT_ID = config("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = config("GOOGLE_CLIENT_SECRET")

# Dynamic redirect URI based on environment
def get_google_redirect_uri(request):
    """
    Get the appropriate redirect URI for Google OAuth based on environment.
    For production: Always use the configured production URL
    For development: Use localhost with the correct port
    """
    # Check if we're on the production domain
    host = request.get_host()
    is_production = 'railway.app' in host or 'repairmybike.in' in host
    
    if is_production:
        # Use the actual host in production
        return f'https://{host}/api/accounts/google/callback/'
    else:
        # For development, always use http://localhost:8000
        return 'http://localhost:8000/api/accounts/google/callback/'

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

            # Try to check login attempts
            try:
                check_login_attempts(email)
            except ValidationError as e:
                return Response({"error": str(e)}, status=status.HTTP_429_TOO_MANY_REQUESTS)
            except Exception as e:
                logger.error(f"Error checking login attempts: {str(e)}")

            # Check if user exists but is not verified
            try:
                user_exists = User.objects.filter(email=email).exists()
                user_obj = User.objects.get(email=email) if user_exists else None
                
                if user_exists and not user_obj.is_active:
                    return Response({
                        "error": "Please verify your email before logging in",
                        "email_verification_required": True,
                        "email": email
                    }, status=status.HTTP_401_UNAUTHORIZED)
            except Exception as e:
                logger.error(f"Error checking user verification status: {str(e)}")

            # Authenticate user
            user = authenticate(request, email=email, password=password)
            
            if not user:
                # Handle failed login attempts
                try:
                    attempts = cache.get(f'login_attempts_{email}', 0)
                    cache.set(f'login_attempts_{email}', attempts + 1, timeout=3600)
                except Exception as e:
                    logger.error(f"Error tracking failed login attempts: {str(e)}")
                
                logger.warning(f"Failed login attempt for {email}")
                
                return Response({
                    "error": "Invalid credentials"
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # Reset login attempts on successful login
            try:
                cache.delete(f'login_attempts_{email}')
                cache.delete(f'account_lockout_{email}')
            except Exception as e:
                logger.error(f"Error clearing login attempts: {str(e)}")
            
            # Log successful login
            logger.info(f"Successful login for {email}")

            # Get tokens and create response
            try:
                tokens = get_tokens_for_user(user)
                is_first_login = user.last_login is None
                
                if is_first_login:
                    logger.info(f"First login after verification for {email}")
                
                response = Response({
                    "message": "Login successful",
                    "is_first_login": is_first_login,
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email,
                        "email_verified": user.email_verified
                    }
                })

                # Set cookies
                response.set_cookie(
                    settings.JWT_AUTH_COOKIE,
                    tokens['access'],
                    max_age=3600,  # 1 hour
                    httponly=True,
                    secure=settings.JWT_AUTH_COOKIE_SECURE,
                    samesite=settings.JWT_AUTH_COOKIE_SAMESITE,
                    path=settings.JWT_AUTH_COOKIE_PATH
                )
                
                response.set_cookie(
                    settings.JWT_AUTH_REFRESH_COOKIE,
                    tokens['refresh'],
                    max_age=30 * 24 * 3600,  # 30 days
                    httponly=True,
                    secure=settings.JWT_AUTH_COOKIE_SECURE,
                    samesite=settings.JWT_AUTH_COOKIE_SAMESITE,
                    path=settings.JWT_AUTH_COOKIE_PATH
                )
                
                return response

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
        redirect_uri = get_google_redirect_uri(request)
        url = (
            f"https://accounts.google.com/o/oauth2/v2/auth?"
            f"client_id={GOOGLE_CLIENT_ID}&"
            f"redirect_uri={redirect_uri}&"
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
            redirect_uri = get_google_redirect_uri(request)
            # Exchange code for tokens
            token_url = "https://oauth2.googleapis.com/token"
            token_data = {
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            }
            token_response = requests.post(token_url, data=token_data)
            token_response.raise_for_status()
            access_token = token_response.json().get("access_token")

            if not access_token:
                logger.error("No access token received from Google")
                return Response(
                    {"error": "Failed to get access token from Google"},
                    status=status.HTTP_400_BAD_REQUEST
                )

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
                logger.info(f"Created new user via Google OAuth: {email}")

            # Generate JWT tokens
            tokens = get_tokens_for_user(user)
            
            # Create response with user data
            response = Response({
                "message": "Login successful",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email
                }
            })

            # Set HttpOnly cookies
            response.set_cookie(
                settings.JWT_AUTH_COOKIE,
                tokens['access'],
                max_age=3600,  # 1 hour
                httponly=True,
                secure=settings.JWT_AUTH_COOKIE_SECURE,
                samesite=settings.JWT_AUTH_COOKIE_SAMESITE,
                path=settings.JWT_AUTH_COOKIE_PATH
            )
            
            response.set_cookie(
                settings.JWT_AUTH_REFRESH_COOKIE,
                tokens['refresh'],
                max_age=30 * 24 * 3600,  # 30 days
                httponly=True,
                secure=settings.JWT_AUTH_COOKIE_SECURE,
                samesite=settings.JWT_AUTH_COOKIE_SAMESITE,
                path=settings.JWT_AUTH_COOKIE_PATH
            )

            # Determine redirect URL based on environment
            if os.environ.get('ENVIRONMENT') == 'production':
                frontend_url = 'https://repairmybike.in'
            else:
                frontend_url = settings.FRONTEND_URL

            response['Location'] = f"{frontend_url}/profile"
            response.status_code = status.HTTP_302_FOUND
            
            return response

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

class SignupView(generics.GenericAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = UserSerializer
    renderer_classes = [JSONRenderer, BrowsableAPIRenderer]

    def get(self, request):
        """Return information about the signup endpoint"""
        return Response({
            "message": "Welcome to the signup endpoint",
            "instructions": "Send a POST request with email, username, and password to create an account",
            "requirements": {
                "email": "Valid email address",
                "username": "Username for your account",
                "password": "Strong password that meets security requirements"
            }
        }, status=status.HTTP_200_OK)

    @method_decorator(csrf_exempt)
    @method_decorator(ratelimit(key='ip', rate='20/h', method=['POST']))
    def post(self, request):
        if getattr(request, 'limited', False):
            return Response({
                "error": "Too many signup attempts. Please try again later.",
                "detail": "Rate limit exceeded"
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)

        serializer = self.get_serializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        email = serializer.validated_data.get('email')
        password = serializer.validated_data.get('password')
        
        # Check if user already exists
        if User.objects.filter(email=email).exists():
            return Response({
                "error": "User with this email already exists"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate password strength
        try:
            validate_password_strength(password)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            
        # Create user account (inactive until email is verified)
        user = serializer.save()
        user.is_active = False  # Disable until email verification
        user.save()
        
        # Generate verification token
        token = get_random_string(64)
        
        # Store in both cache and database for redundancy
        try:
            # Store in cache with 24 hour expiry
            cache.set(f'email_verification_{token}', user.pk, timeout=86400)
            
            # Also store in database
            EmailVerificationToken.objects.create(
                user=user,
                token=token
            )
            
            # Get the environment
            environment = os.environ.get('ENVIRONMENT', 'development')
            
            # Generate verification URL
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
                
            verification_url = f"{frontend_url}/verify-email/{token}"
            
            logger.info(f"Generated verification URL with frontend_url: {frontend_url}")
            
            # Send verification email using EMAIL_HOST_USER as sender
            send_mail(
                subject="Verify Your Email - Repair My Bike",
                message=f"""Thank you for signing up with Repair My Bike!

Please click the link below to verify your email address:

{verification_url}

This link will expire in 24 hours.

If you did not create an account, please ignore this email.

Best regards,
The Repair My Bike Team""",
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[user.email],
                fail_silently=False,
            )
            
            # Log signup
            logger.info(f"New user signed up: {email}")
            
            return Response({
                "message": "Registration successful! Please check your email to verify your account.",
                "email": email,
                "verification_required": True,
                "next_step": "Please verify your email before logging in. Check your inbox for a verification link."
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            # If email sending fails, delete the user and return error
            user.delete()
            logger.error(f"Signup error: {str(e)}")
            return Response({
                "error": "Failed to create account. Please try again later."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class VerifyEmailView(APIView):
    permission_classes = (permissions.AllowAny,)

    def get(self, request, token):
        try:
            # Try to get user_id from cache first
            user_id = cache.get(f'email_verification_{token}')
            
            if not user_id:
                # If not in cache, check if token exists in database
                verification_token = EmailVerificationToken.objects.filter(
                    token=token,
                    created_at__gte=timezone.now() - timezone.timedelta(hours=24)
                ).first()
                
                if verification_token:
                    user_id = verification_token.user.id
                else:
                    return Response({
                        "error": "Invalid or expired verification link",
                        "status": "error"
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                user = User.objects.get(pk=user_id)
                if not user.is_active:
                    user.is_active = True
                    user.email_verified = True
                    user.save()
                    
                    try:
                        # Try to clear verification token from cache
                        cache.delete(f'email_verification_{token}')
                        # Also delete from database if it exists
                        EmailVerificationToken.objects.filter(token=token).delete()
                    except Exception as e:
                        logger.warning(f"Failed to delete verification token: {str(e)}")
                    
                    logger.info(f"Email verified for user: {user.email}")
                    
                    # Get the environment
                    environment = os.environ.get('ENVIRONMENT', 'development')
                    
                    # Generate login URL
                    # For production, always use the production domain
                    if environment == 'production':
                        frontend_url = 'https://repairmybike.in'
                    else:
                        # For development, try to determine frontend URL from headers
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
                    
                    login_url = f"{frontend_url}/login-signup"
                    
                    return Response({
                        "message": "Email verified successfully. You can now log in with your credentials.",
                        "status": "success",
                        "verified": True,
                        "user": {
                            "email": user.email,
                        },
                        "redirect_url": login_url
                    }, status=status.HTTP_200_OK)
                
                # Get the environment
                environment = os.environ.get('ENVIRONMENT', 'development')
                
                # Generate login URL using same logic as above
                if environment == 'production':
                    frontend_url = 'https://repairmybike.in'
                else:
                    # For development, try to determine frontend URL from headers
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
                
                login_url = f"{frontend_url}/login-signup"
                
                return Response({
                    "message": "Email already verified. You can log in with your credentials.",
                    "status": "success",
                    "verified": True,
                    "user": {
                        "email": user.email,
                    },
                    "redirect_url": login_url
                }, status=status.HTTP_200_OK)
                
            except User.DoesNotExist:
                logger.error(f"Verification failed: User not found for token {token}")
                return Response({
                    "error": "User not found",
                    "status": "error"
                }, status=status.HTTP_404_NOT_FOUND)
                
        except Exception as e:
            logger.error(f"Email verification error: {str(e)}")
            return Response({
                "error": "An error occurred during email verification",
                "status": "error"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class LogoutView(APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        try:
            # Get refresh token from cookie
            refresh_token = request.COOKIES.get(settings.JWT_AUTH_REFRESH_COOKIE)
            
            if refresh_token:
                try:
                    # Blacklist the refresh token
                    token = RefreshToken(refresh_token)
                    token.blacklist()
                except TokenError:
                    # Token might be invalid, but we still want to clear cookies
                    pass
            
            # Create response
            response = Response({"message": "Successfully logged out"})
            
            # Delete cookies
            response.delete_cookie(settings.JWT_AUTH_COOKIE)
            response.delete_cookie(settings.JWT_AUTH_REFRESH_COOKIE)
            
            # Try to log the logout if user is authenticated
            if request.user.is_authenticated:
                logger.info(f"User {request.user.email} logged out successfully")
            else:
                logger.info("User logged out successfully (unauthenticated)")
            
            return response
            
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
    try:
        if request.method == 'GET':
            profile = UserProfile.objects.get(user=request.user)
            serializer = UserProfileSerializer(profile)
            return Response(serializer.data)
            
        elif request.method == 'POST':
            # Check if profile exists
            profile = UserProfile.objects.filter(user=request.user).first()
            
            if profile:
                # Update existing profile
                serializer = UserProfileSerializer(profile, data=request.data, partial=True)
            else:
                # Create new profile
                data = request.data.copy()
                data['user'] = request.user.id
                serializer = UserProfileSerializer(data=data)
                
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        return Response(
            {'detail': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )

class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    
    def get(self, request):
        """Get user profile"""
        try:
            profile, created = UserProfile.objects.get_or_create(user=request.user)
            if created:
                profile.name = request.user.get_full_name() or request.user.username
                profile.save()
            serializer = UserProfileSerializer(profile)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error retrieving user profile: {str(e)}")
            return Response(
                {"detail": f"Error retrieving profile: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def post(self, request):
        """Create or update user profile"""
        try:
            # Check if profile exists, create it if not
            profile, created = UserProfile.objects.get_or_create(user=request.user)
            
            # Determine if the request contains JSON or form data
            if request.content_type and 'application/json' in request.content_type:
                # JSON data
                data = request.data
            else:
                # Form data (with potential file upload)
                data = request.data
                
                # If JSON was passed as a string in 'data' field, parse it
                if 'data' in data and isinstance(data['data'], str):
                    try:
                        json_data = json.loads(data['data'])
                        # Merge form data and JSON data
                        for key, value in json_data.items():
                            if key not in data:
                                data[key] = value
                    except json.JSONDecodeError:
                        pass
            
            # Update serializer with the request data
            serializer = UserProfileSerializer(profile, data=data, partial=True)
                
            if serializer.is_valid():
                profile = serializer.save()
                return Response(
                    UserProfileSerializer(profile).data, 
                    status=status.HTTP_200_OK
                )
            
            return Response(
                serializer.errors, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error updating user profile: {str(e)}")
            return Response(
                {"detail": f"Error updating profile: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def patch(self, request):
        """Partially update user profile"""
        try:
            # Get or create the user profile
            profile, created = UserProfile.objects.get_or_create(user=request.user)
            if created:
                profile.name = request.user.get_full_name() or request.user.username
                profile.save()
                
            # Log the incoming data for debugging
            logger.info(f"PATCH request for profile update received with data: {request.data}")
            
            # Handle JSON data
            if request.content_type and 'application/json' in request.content_type:
                data = request.data
            else:
                # Handle form data and files
                data = request.data.copy()
                
                # Parse JSON data if provided in 'data' field
                if 'data' in data and isinstance(data['data'], str):
                    try:
                        json_data = json.loads(data['data'])
                        for key, value in json_data.items():
                            data[key] = value
                    except json.JSONDecodeError as e:
                        logger.error(f"Error parsing JSON data: {str(e)}")
            
            # Convert field names from frontend format to model format if needed
            if 'postalCode' in data:
                data['postal_code'] = data.pop('postalCode')
            
            # Use the serializer with partial=True for PATCH operations
            serializer = UserProfileSerializer(profile, data=data, partial=True)
            
            if serializer.is_valid():
                updated_profile = serializer.save()
                logger.info(f"Profile updated successfully for user {request.user.email}")
                return Response(
                    UserProfileSerializer(updated_profile).data,
                    status=status.HTTP_200_OK
                )
            else:
                logger.warning(f"Profile update validation failed: {serializer.errors}")
                return Response(
                    serializer.errors,
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Exception as e:
            logger.exception(f"Error in profile patch: {str(e)}")
            return Response(
                {"detail": f"Error updating profile: {str(e)}"},
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