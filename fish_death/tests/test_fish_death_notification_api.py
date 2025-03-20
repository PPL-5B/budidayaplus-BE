import json
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from ninja_jwt.tokens import AccessToken
from datetime import timedelta
from django.utils import timezone
from pond.models import Pond
from cycle.models import Cycle, PondFishAmount
from fish_death.models import FishDeath
from fish_death.models import FishDeathNotification 

class FishDeathNotificationAPITestCase(TestCase):
    
    def setUp(self):
        self.user = User.objects.create_user(username="081234567890", password="password")
        self.token = str(AccessToken.for_user(self.user))

        self.pond = Pond.objects.create(
            pond_id="test-pond-id",
            name="Test Pond",
            owner=self.supervisor
        )

        now = timezone.now()
        self.cycle = Cycle.objects.create(
            start_date=now.date(),
            end_date=(now + timedelta(days=10)).date(),
            supervisor=self.supervisor,
            is_stopped=False
        )

        self.pond_fish_amount = PondFishAmount.objects.create(
            pond=self.pond,
            cycle=self.cycle,
            fish_amount=100
        )

        self.client = self.client_class()

    
    def test_fish_death_creates_notification(self):
        """
        Test that adding fish death data creates a notification for the pond owner.
        """
        url = f"/fish_death/{self.pond.pond_id}/{self.cycle.id}/"
        payload = {
            "fish_death_count": 10
        }

        response = self.client.post(
            url,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.token}",
        )

        # Check the response
        self.assertEqual(response.status_code, 200)
        self.assertIn("message", response.json())
        self.assertEqual(response.json()["message"], "Fish death data recorded successfully.")

        # Check that a notification was created
        notification = FishDeathNotification.objects.filter(user=self.supervisor).first()
        self.assertIsNotNone(notification)
        self.assertEqual(notification.title, "Fish Death Alert")
        self.assertIn("10 fish deaths reported in Test Pond", notification.message)