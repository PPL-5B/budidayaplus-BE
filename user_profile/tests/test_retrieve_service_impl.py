from django.test import TestCase
from django.contrib.auth.models import User
from user_profile.models import UserProfile
from user_profile.services.retrieve_service_impl import RetrieveServiceImpl
from django.core.exceptions import ObjectDoesNotExist


class RetrieveServiceImplTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="password123",
            first_name="Test",
            last_name="User"
        )
        self.profile = UserProfile.objects.create(
            user=self.user,
            image_name="profile.png"
        )

    def test_retrieve_user_success(self):
        user = RetrieveServiceImpl.retrieve_user("testuser")
        self.assertEqual(user.username, "testuser")

    def test_retrieve_user_not_found(self):
        with self.assertRaises(User.DoesNotExist):
            RetrieveServiceImpl.retrieve_user("unknownuser")

    def test_retrieve_profile_success(self):
        profile = RetrieveServiceImpl.retrieve_profile("testuser")
        self.assertEqual(profile.user, self.user)

    def test_retrieve_profile_not_found(self):
        with self.assertRaises(UserProfile.DoesNotExist):
            RetrieveServiceImpl.retrieve_profile("unknownuser")

    def test_retrieve_profile_by_user_success(self):
        profile = RetrieveServiceImpl.retrieve_profile_by_user(self.user)
        self.assertEqual(profile.user.username, "testuser")

    def test_retrieve_profile_by_user_not_found(self):
        new_user = User.objects.create_user(username="nouser", password="123456")
        with self.assertRaises(UserProfile.DoesNotExist):
            RetrieveServiceImpl.retrieve_profile_by_user(new_user)
