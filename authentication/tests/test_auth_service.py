from django.test import TestCase
from django.contrib.auth.models import User
from authentication.services.auth_service import AuthenticationService
from ninja.errors import HttpError
from ninja_jwt.tokens import RefreshToken
from datetime import timedelta

class TestAuthService(TestCase):
    def test_login_success(self):
        User.objects.create_user(username="testuser", password="password123")
        response = AuthenticationService.login("testuser", "password123")
        self.assertEqual(response["message"], "Login berhasil")
        self.assertIn("access", response)
        self.assertIn("refresh", response)

    def test_login_invalid_credentials(self):
        User.objects.create_user(username="testuser", password="password123")
        with self.assertRaises(HttpError):
            AuthenticationService.login("testuser", "wrongpassword")

    def test_login_user_not_found(self):
        with self.assertRaises(HttpError):
            AuthenticationService.login("nonexistentuser", "password123")

    def test_register_success(self):
        response = AuthenticationService.register("newuser", "First", "Last", "password123")
        self.assertEqual(response["message"], "Akun berhasil dibuat")
        self.assertIn("access", response)
        self.assertIn("refresh", response)

    def test_register_existing_user(self):
        User.objects.create_user(username="testuser", password="password123")
        with self.assertRaises(HttpError):
            AuthenticationService.register("testuser", "First", "Last", "password123")

    def test_refresh_token_success(self):
        user = User.objects.create_user(username="testuser", password="password123")
        refresh = RefreshToken.for_user(user)
        response = AuthenticationService.refresh_token(str(refresh))
        self.assertIn("access", response)

    def test_refresh_token_invalid(self):
        with self.assertRaises(HttpError):
            AuthenticationService.refresh_token("invalidtoken")

    def test_validate_token(self):
        user = User.objects.create_user(username="testuser", password="password123")
        self.assertEqual(AuthenticationService.validate_token(user)["message"], "Token valid")

    def test_get_user_details(self):
        user = User.objects.create_user(username="testuser", password="password123", first_name="First", last_name="Last")
        response = AuthenticationService.get_user_details(user)
        self.assertEqual(response["id"], user.id)
        self.assertEqual(response["phone_number"], "testuser")
        self.assertEqual(response["first_name"], "First")
        self.assertEqual(response["last_name"], "Last")
    
    # Negative Cases
    def test_login_empty_username(self):
        with self.assertRaises(HttpError):
            AuthenticationService.login("", "password123")

    def test_refresh_token_expired(self):
        user = User.objects.create_user(username="testuser", password="password123")
        refresh = RefreshToken.for_user(user)
        refresh.set_exp(lifetime=timedelta(seconds=-1))  # Expire the token
        with self.assertRaises(HttpError):
            AuthenticationService.refresh_token(str(refresh))

    # Edge Cases
    def test_login_max_length_username(self):
        max_length_username = "u" * 150
        User.objects.create_user(username=max_length_username, password="password123")
        response = AuthenticationService.login(max_length_username, "password123")
        self.assertEqual(response["message"], "Login berhasil")

    def test_register_max_length_fields(self):
        max_length_username = "u" * 150
        max_length_name = "n" * 150
        response = AuthenticationService.register(max_length_username, max_length_name, max_length_name, "password123")
        self.assertEqual(response["message"], "Akun berhasil dibuat")