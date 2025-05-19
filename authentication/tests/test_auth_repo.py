from django.test import TestCase
from django.contrib.auth.models import User
from authentication.repositories.auth_repo import UserRepository

class TestAuthRepo(TestCase):
    def test_get_user_by_username(self):
        user = User.objects.create_user(username="testuser", password="password123")
        retrieved_user = UserRepository.get_user_by_username("testuser")
        self.assertEqual(retrieved_user, user)

    def test_get_user_by_username_not_found(self):
        with self.assertRaises(User.DoesNotExist):
            UserRepository.get_user_by_username("nonexistentuser")

    def test_user_exists(self):
        User.objects.create_user(username="testuser", password="password123")
        self.assertTrue(UserRepository.user_exists("testuser"))

    def test_user_exists_not_found(self):
        self.assertFalse(UserRepository.user_exists("nonexistentuser"))

    def test_create_user(self):
        user = UserRepository.create_user("newuser", "password123", "First", "Last")
        self.assertEqual(user.username, "newuser")
        self.assertEqual(user.first_name, "First")
        self.assertEqual(user.last_name, "Last")

    def test_create_user_invalid(self):
        with self.assertRaises(ValueError):
            UserRepository.create_user("", "password123", "First", "Last")

    def test_get_user_by_id(self):
        user = User.objects.create_user(username="testuser", password="password123")
        self.assertTrue(UserRepository.get_user_by_id(user.id))

    def test_get_user_by_id_not_found(self):
        self.assertFalse(UserRepository.get_user_by_id(9999))

    # Negative Cases
    def test_get_user_by_empty_username(self):
        with self.assertRaises(User.DoesNotExist):
            UserRepository.get_user_by_username("")

    def test_get_user_by_nonexistent_id(self):
        self.assertFalse(UserRepository.get_user_by_id(9999))

    # Edge Cases
    def test_create_user_max_length_fields(self):
        max_length_username = "u" * 150
        max_length_name = "n" * 150
        user = UserRepository.create_user(max_length_username, "password123", max_length_name, max_length_name)
        self.assertEqual(user.username, max_length_username)
        self.assertEqual(user.first_name, max_length_name)
        self.assertEqual(user.last_name, max_length_name)

    def test_user_exists_special_characters(self):
        User.objects.create_user(username="user!@#", password="password123")
        self.assertTrue(UserRepository.user_exists("user!@#"))