from django.test import TestCase
from django.contrib.auth.models import User
from user_profile.models import UserProfile
from user_profile.services.update_service_impl import UpdateServiceImpl
from user_profile.schemas import UpdateProfileSchema


class UpdateServiceImplTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="tester", password="secret", first_name="Old", last_name="Name"
        )
        self.profile = UserProfile.objects.create(
            user=self.user,
            image_name="old_image.png"
        )

    def test_update_profile_successfully(self):
        payload = UpdateProfileSchema(
            first_name="New",
            last_name="Updated",
            image_name="new_image.jpg"
        )

        result = UpdateServiceImpl.update_profile(payload, self.user)

        # Refresh from DB
        self.user.refresh_from_db()
        self.profile.refresh_from_db()

        self.assertEqual(self.user.first_name, "New")
        self.assertEqual(self.user.last_name, "Updated")
        self.assertEqual(self.profile.image_name, "new_image.jpg")

        self.assertIsInstance(result, UpdateProfileSchema)
        self.assertEqual(result.first_name, "New")
        self.assertEqual(result.last_name, "Updated")
        self.assertEqual(result.image_name, "new_image.jpg")
