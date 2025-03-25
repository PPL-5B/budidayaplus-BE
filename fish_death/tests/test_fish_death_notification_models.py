from django.test import TestCase
from django.contrib.auth.models import User
from fish_death.models import FishDeathNotification
from django.utils.timezone import now


class FishDeathNotificationModelTest(TestCase):
    def setUp(self):
        # Create a user
        self.user = User.objects.create_user(username="testuser", password="password")

        # Create a FishDeathNotification instance
        self.notification = FishDeathNotification.objects.create(
            user=self.user,
            title="Fish Death Alert",
            message="10 fish deaths reported in Test Pond.",
            created_at=now()
        )

    def test_notification_creation(self):
        """Test that a FishDeathNotification instance is created correctly."""
        self.assertEqual(self.notification.user, self.user)
        self.assertEqual(self.notification.title, "Fish Death Alert")
        self.assertEqual(self.notification.message, "10 fish deaths reported in Test Pond.")
        self.assertIsNotNone(self.notification.created_at)

    def test_notification_str_method(self):
        """Test the __str__ method of the FishDeathNotification model."""
        self.assertEqual(str(self.notification), "Fish Death Alert")