from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient


class AuthFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.signup_payload = {
            'username': 'smartfarmer',
            'email': 'smartfarmer@example.com',
            'password': 'SecurePass123',
        }

    def test_signup_login_logout_flow(self):
        signup_response = self.client.post('/auth/signup/', self.signup_payload, format='json')
        self.assertEqual(signup_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(signup_response.data['message'], 'Signup successful')
        self.assertEqual(signup_response.data['user']['email'], self.signup_payload['email'])

        login_response = self.client.post(
            '/auth/login/',
            {
                'email': self.signup_payload['email'],
                'password': self.signup_payload['password'],
            },
            format='json',
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.assertTrue(login_response.data['authenticated'])
        self.assertEqual(self.client.session.get('_auth_user_id'), str(User.objects.get().id))

        logout_response = self.client.post('/auth/logout/', {}, format='json')
        self.assertEqual(logout_response.status_code, status.HTTP_200_OK)
        self.assertFalse(logout_response.data['authenticated'])
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_signup_rejects_duplicate_email(self):
        User.objects.create_user(
            username='existing-user',
            email=self.signup_payload['email'],
            password='SecurePass123',
        )

        response = self.client.post('/auth/signup/', self.signup_payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['message'], 'Signup failed')
        self.assertIn('email', response.data['errors'])
