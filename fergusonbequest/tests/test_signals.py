from django.utils.crypto import get_random_string
from django.test import TestCase
from django.contrib.auth import get_user_model
from fergusonbequest.models import Profile

User = get_user_model()


def unique_email():
    return f"sig-{get_random_string(8)}@example.com"


class ProfileSignalTests(TestCase):
    def test_profile_created_on_user_create(self):
        """Creating a User should also create a Profile via signals.

        How the test works:
        - Create a user with User.objects.create_user.
        - Query the Profile table for an entry with that user

        Parameters:
        - username (str): auto-generated username passed to create_user
        - email (str): unique email generated for the test

        Expected output:
        - A `Profile` object exists and is associated with the newly created User

        Pass: Profile exists (not None). Fail: Profile is None/missing.
        """
        u = User.objects.create_user(username=get_random_string(6), email=unique_email(), password='pw')
        profile = Profile.objects.filter(user=u).first()
        self.assertIsNotNone(profile)

    def test_profile_created_on_registration_view(self):
        """Registering via the public view should also create a Profile.

        How the test works:
        - POST registration data to `/register/`
        - Ensure response indicates success.
        - Retrieve the created User and assert a Profile exists

        Parameters (POST data):
        - first_name, last_name (str)
        - email (str): the registered email
        - password, password_confirm (str)

        Expected output:
        - HTTP 302 response indicating registration success
        - A `Profile` object associated with the newly created user

        Pass: 302 response and Profile exists. Fail: non-302 or missing Profile.
        """
        email = unique_email()
        resp = self.client.post('/register/', {
            'first_name': 'Sig',
            'last_name': 'User',
            'email': email,
            'password': 'Complexpass123',
            'password_confirm': 'Complexpass123'
        })
        self.assertEqual(resp.status_code, 302)
        u = User.objects.get(email__iexact=email)
        self.assertTrue(Profile.objects.filter(user=u).exists())
