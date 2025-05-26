from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings

class CustomTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        # Get refresh token from request data
        refresh_token = request.data.get('refresh')
        
        if not refresh_token:
            return Response(
                {"error": "No refresh token provided in request body"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Process the refresh token and generate new access token
        response = super().post(request, *args, **kwargs)
        
        if response.status_code == 200:
            # Return both access and refresh tokens in response
            return Response({
                'access': response.data['access'],
                'refresh': response.data.get('refresh', refresh_token),
                'message': "Token refresh successful"
            })
        
        return response 