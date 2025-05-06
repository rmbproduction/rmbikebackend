# accounts/urls.py
from django.urls import path
from . import views
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('', views.accounts_root_view, name='accounts-root'),
    path('signup/', views.SignupView.as_view(), name='signup'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('password-reset/', views.PasswordResetView.as_view(), name='password_reset'),
    path('password-reset/<str:token>/', views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('verify-email/<str:token>/', views.VerifyEmailView.as_view(), name='verify_email'),
    path('google/login/', views.GoogleLoginView.as_view(), name='google_login'),
    path('google/callback/', views.GoogleCallbackView.as_view(), name='google_callback'),
    path('contact/', views.ContactMessageView.as_view(), name='contact'),
    path('profile/', views.UserProfileView.as_view(), name='user-profile'),
]