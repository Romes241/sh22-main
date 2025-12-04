from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from .utils import unique_email, unique_username

User = get_user_model()


class EmailLoginTests(TestCase):
    def setUp(self):
        self.email = unique_email()
        self.password = "ComplexPass123"
        self.user = User.objects.create_user(
            username=unique_username(), email=self.email, password=self.password
        )

    def test_login_with_email_success(self):
        """POST to the login view with correct email+password redirects.

        How the test works:
        - posts credentials to the login URL
        - expects a 302 redirect on success

        Parameters:
        - username (str): the user's email address
        - password (str): the user's password

        Expected output:
        - HTTP 302 response (redirect to dashboard or next URL)

        Pass: response status code is 302.
        Fail: status code is not 302.
        """
        resp = self.client.post(reverse('login'), {'username': self.email, 'password': self.password})
        # successful login should redirect
        self.assertEqual(resp.status_code, 302)

    def test_login_with_email_case_insensitive(self):
        """Ensure email matching is case-insensitive.

        The login view should accept the email regardless of case.

        Parameters:
        - username (str): the user's email in a different case (uppercased)
        - password (str): the user's password

        Expected output:
        - HTTP 302 response (successful login despite case differences)

        Pass: status code 302. Fail: not 302.
        """
        resp = self.client.post(reverse('login'), {'username': self.email.upper(), 'password': self.password})
        self.assertEqual(resp.status_code, 302)

    def test_login_wrong_password_shows_error(self):
        """Submitting a wrong password should re-render the form with an error.

        The view should not redirect; it should return 200 and include the
        friendly non-field error message guiding the user.

        Parameters:
        - username (str): the user's email address
        - password (str): an incorrect password string

        Expected output:
        - HTTP 200 response (form re-displayed)
        - page contains the text: 'Please ensure your email and password are correct'

        Pass: status_code == 200 and page contains the friendly error text.
        Fail: redirect occurs (302) or the expected error message is missing.
        """
        resp = self.client.post(reverse('login'), {'username': self.email, 'password': 'wrong'})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Please ensure your email and password are correct')
