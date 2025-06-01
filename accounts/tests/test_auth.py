from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from accounts.models import User
from django.core.cache import cache

class AuthenticationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.signup_url = reverse('signup')
        self.login_url = reverse('login')
        self.logout_url = reverse('logout')
        self.test_user_data = {
            'email': 'test@example.com',
            'password': 'Test@123456',
            'first_name': 'Test',
            'last_name': 'User'
        }
        
    def tearDown(self):
        cache.clear()
        
    def test_user_signup_success(self):
        response = self.client.post(self.signup_url, self.test_user_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email=self.test_user_data['email']).exists())
        
    def test_user_signup_weak_password(self):
        weak_password_data = self.test_user_data.copy()
        weak_password_data['password'] = '123456'
        response = self.client.post(self.signup_url, weak_password_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
    def test_user_login_success(self):
        # Create user first
        User.objects.create_user(**self.test_user_data)
        
        # Attempt login
        response = self.client.post(self.login_url, {
            'email': self.test_user_data['email'],
            'password': self.test_user_data['password']
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        
    def test_user_login_wrong_credentials(self):
        response = self.client.post(self.login_url, {
            'email': 'wrong@example.com',
            'password': 'wrongpass'
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
    def test_user_logout(self):
        # Create and login user
        User.objects.create_user(**self.test_user_data)
        login_response = self.client.post(self.login_url, {
            'email': self.test_user_data['email'],
            'password': self.test_user_data['password']
        })
        
        # Set token in header
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")
        
        # Attempt logout
        response = self.client.post(self.logout_url, {'refresh': login_response.data['refresh']})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
    def test_rate_limiting(self):
        # Test rate limiting by making multiple requests
        for _ in range(6):  # Assuming rate limit is 5 requests per minute
            self.client.post(self.login_url, {
                'email': 'test@example.com',
                'password': 'wrongpass'
            })
        
        response = self.client.post(self.login_url, {
            'email': 'test@example.com',
            'password': 'wrongpass'
        })
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS) 