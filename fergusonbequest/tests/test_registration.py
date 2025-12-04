from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from .utils import unique_email, unique_username

User = get_user_model()


class RegistrationTests(TestCase):
    def test_register_creates_user_and_normalises_email(self):
        """Posting valid registration data should create a User and normalise email.

        Mechanism:
        - POSTs a filled registration form to the `register` URL.
        - Expects a 302 redirect on success.
        - Loads the created user and checks that the saved email is normalised to lowercase.

        Pass: response is 302 and stored email.lower() matches submitted.lower().
        Fail: response is not 302 or stored email case doesn't match expectation.
        """
        url = reverse('register')
        email = unique_email()
        data = {
            'first_name': 'New',
            'last_name': 'User',
            'email': email,
            'password': 'Complexpass123',
            'password_confirm': 'Complexpass123',
        }
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 302)
        user = User.objects.get(email__iexact=email)
        self.assertEqual(user.email.lower(), email.lower())

    def test_register_duplicate_email_rejected(self):
        """Submitting a registration with an existing email should re-display the form.

        Mechanism:
        - Create an existing user with a base email.
        - POST a registration using the same email in a different case.
        - Expect status code 200 and an error message.

        Pass: response is 200 and contains the duplicate-email message.
        Fail: a user is created (302) or message/status differ.
        """
        base_email = unique_email()
        User.objects.create_user(username=unique_username(), email=base_email, password='x')
        url = reverse('register')
        data = {
            'first_name': 'X',
            'last_name': 'Y',
            'email': base_email.upper(),
            'password': 'Password123',
            'password_confirm': 'Password123',
        }
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'A user with that email already exists')
