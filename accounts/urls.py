# accounts/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.accounts_root_view, name='accounts-root'),
    path('signup/', views.SignupView.as_view(), name='signup'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('token/refresh/', views.TokenRefreshView.as_view(), name='token-refresh'),
    path('verify-email/<str:token>/', views.VerifyEmailView.as_view(), name='verify-email'),
    path('resend-verification/', views.ResendVerificationView.as_view(), name='resend-verification'),
    path('password/reset/', views.PasswordResetView.as_view(), name='password-reset'),
    path('password/reset/<str:token>/', views.PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('profile/', views.UserProfileView.as_view(), name='user-profile'),
    path('contact/', views.ContactMessageView.as_view(), name='contact'),
    path('google/url/', views.GoogleLoginView.as_view(), name='google-login'),
    path('google/callback/', views.GoogleCallbackView.as_view(), name='google-callback'),
]