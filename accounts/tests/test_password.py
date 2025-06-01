from django.test import TestCase
from django.urls import reverse
from django.core import mail
from django.core.cache import cache
from rest_framework.test import APIClient
from rest_framework import status
from accounts.models import User
import re

class PasswordResetTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.reset_request_url = reverse('password_reset')
        self.test_user_data = {
            'email': 'test@example.com',
            'password': 'Test@123456',
            'first_name': 'Test',
            'last_name': 'User'
        }
        # Create test user
        self.user = User.objects.create_user(**self.test_user_data)
        
    def tearDown(self):
        cache.clear()
        
    def test_password_reset_request_success(self):
        response = self.client.post(self.reset_request_url, {
            'email': self.test_user_data['email']
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check if email was sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to[0], self.test_user_data['email'])
        
    def test_password_reset_request_nonexistent_email(self):
        response = self.client.post(self.reset_request_url, {
            'email': 'nonexistent@example.com'
        })
        # Should still return 200 for security (don't reveal if email exists)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # But no email should be sent
        self.assertEqual(len(mail.outbox), 0)
        
    def test_password_reset_rate_limiting(self):
        # Make 4 reset requests (limit is 3 per hour)
        for _ in range(4):
            response = self.client.post(self.reset_request_url, {
                'email': self.test_user_data['email']
            })
        # Last request should be rate limited
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        
    def test_password_reset_confirm_success(self):
        # First request reset
        self.client.post(self.reset_request_url, {
            'email': self.test_user_data['email']
        })
        
        # Extract token from email
        email_content = mail.outbox[0].body
        token_match = re.search(r'/password-reset/([^/\s]+)', email_content)
        token = token_match.group(1)
        
        # Confirm reset with new password
        reset_confirm_url = reverse('password_reset_confirm', kwargs={'token': token})
        new_password = 'NewTest@123456'
        response = self.client.post(reset_confirm_url, {
            'password': new_password,
            'confirm_password': new_password
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify can login with new password
        login_response = self.client.post(reverse('login'), {
            'email': self.test_user_data['email'],
            'password': new_password
        })
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        
    def test_password_reset_confirm_weak_password(self):
        # First request reset
        self.client.post(self.reset_request_url, {
            'email': self.test_user_data['email']
        })
        
        # Extract token from email
        email_content = mail.outbox[0].body
        token_match = re.search(r'/password-reset/([^/\s]+)', email_content)
        token = token_match.group(1)
        
        # Try to reset with weak password
        reset_confirm_url = reverse('password_reset_confirm', kwargs={'token': token})
        response = self.client.post(reset_confirm_url, {
            'password': '123456',
            'confirm_password': '123456'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
    def test_password_reset_confirm_invalid_token(self):
        reset_confirm_url = reverse('password_reset_confirm', kwargs={'token': 'invalid-token'})
        response = self.client.post(reset_confirm_url, {
            'password': 'NewTest@123456',
            'confirm_password': 'NewTest@123456'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST) 