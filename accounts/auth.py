from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings

class CustomTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        # Get refresh token from cookie
        refresh_token = request.COOKIES.get(settings.JWT_AUTH_REFRESH_COOKIE)
        
        if not refresh_token:
            return Response(
                {"error": "No refresh token cookie found"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Add refresh token to request data
        request.data['refresh'] = refresh_token
        
        # Get response from parent class
        response = super().post(request, *args, **kwargs)
        
        if response.status_code == 200:
            # Set new access token in cookie
            response.set_cookie(
                settings.JWT_AUTH_COOKIE,
                response.data['access'],
                max_age=3600,
                httponly=True,
                secure=settings.JWT_AUTH_COOKIE_SECURE,
                samesite=settings.JWT_AUTH_COOKIE_SAMESITE,
                path=settings.JWT_AUTH_COOKIE_PATH
            )
            
            # Remove tokens from response body
            response.data = {"message": "Token refresh successful"}
        
        return response 