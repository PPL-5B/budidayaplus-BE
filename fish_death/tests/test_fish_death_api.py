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

class FishDeathAPITestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass"
        )
        self.token = str(AccessToken.for_user(self.user))

        self.pond = Pond.objects.create(
            pond_id="test-pond-id",
            name="Test Pond"
        )

        now = timezone.now()
        self.cycle = Cycle.objects.create(
            start_date=now.date(),
            end_date=(now + timedelta(days=10)).date(),
            supervisor=self.user,
            is_stopped=False
        )

        self.pond_fish_amount = PondFishAmount.objects.create(
            pond=self.pond,
            cycle=self.cycle,
            fish_amount=100
        )

        self.client = self.client_class()

    def test_create_fish_death(self):
        """
        Test that we can create a new FishDeath record and that PondFishAmount is decremented.
        """
        url = f"/fish_death/{self.pond.pond_id}/{self.cycle.id}/"
        payload = {
            "fish_death_count": 5
        }

        response = self.client.post(
            url,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.token}",
        )

        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()

        self.assertIn("id", data)
        self.assertIn("fish_death_count", data)
        self.assertIn("fish_alive_count", data)

        self.assertEqual(data["fish_death_count"], 5)

        self.assertEqual(data["fish_alive_count"], 100)

        self.pond_fish_amount.refresh_from_db()
        self.assertEqual(self.pond_fish_amount.fish_amount, 95)

        fish_death = FishDeath.objects.get(id=data["id"])
        self.assertEqual(fish_death.fish_death_count, 5)
        self.assertEqual(fish_death.fish_alive_count, 100)

    def test_get_latest_fish_death(self):
        """
        Test that we can retrieve the most recently created FishDeath record.
        """
        FishDeath.objects.create(
            cycle=self.cycle,
            pond=self.pond,
            reporter=self.user,
            fish_death_count=3,
            fish_alive_count=100,
            recorded_at=timezone.now() - timedelta(hours=2)
        )
        latest = FishDeath.objects.create(
            cycle=self.cycle,
            pond=self.pond,
            reporter=self.user,
            fish_death_count=2,
            fish_alive_count=97,
            recorded_at=timezone.now()
        )

        url = f"/fish_death/{self.pond.pond_id}/{self.cycle.id}/latest/"
        response = self.client.get(
            url,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.token}",
        )
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()

        self.assertEqual(str(latest.id), data["id"])
        self.assertEqual(data["fish_death_count"], 2)
        self.assertEqual(data["fish_alive_count"], 97)

    def test_list_fish_death(self):
        """
        Test listing all FishDeath records for the active cycle in a given pond.
        """
        fd1 = FishDeath.objects.create(
            cycle=self.cycle,
            pond=self.pond,
            reporter=self.user,
            fish_death_count=1,
            fish_alive_count=100,
            recorded_at=timezone.now() - timedelta(days=1)
        )
        fd2 = FishDeath.objects.create(
            cycle=self.cycle,
            pond=self.pond,
            reporter=self.user,
            fish_death_count=4,
            fish_alive_count=95,
            recorded_at=timezone.now()
        )

        url = f"/fish_death/{self.pond.pond_id}/"
        response = self.client.get(
            url,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.token}",
        )
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()

        self.assertIn("fish_deaths", data)
        self.assertIn("cycle_id", data)
        self.assertEqual(data["cycle_id"], str(self.cycle.id))

        fish_deaths_list = data["fish_deaths"]
        self.assertEqual(len(fish_deaths_list), 2)
        self.assertEqual(fish_deaths_list[0]["id"], str(fd2.id))
        self.assertEqual(fish_deaths_list[1]["id"], str(fd1.id))


class FishDeathNotificationTest(TestCase):
    def setUp(self):
        self.client = TestClient(router)

        # Create Supervisor
        self.supervisor = User.objects.create_user(username='supervisor', password='password', is_staff=True)
        self.supervisor_profile, _ = UserProfile.objects.get_or_create(user=self.supervisor)

        # Create Worker with Supervisor
        self.user = User.objects.create_user(username='userA', password='abc123')
        self.worker = Worker.objects.create(user=self.user, assigned_supervisor=self.supervisor_profile)

        self.pond = Pond.objects.create(
            owner=self.supervisor,
            name='Test Pond',
            image_name='test_pond.png',
            length=10.0,
            width=5.0,
            depth=2.0
        )

        start_time = make_aware(datetime.now()) - timedelta(days=30)
        end_time = start_time + timedelta(days=60)
        self.cycle = Cycle.objects.create(
            supervisor=self.supervisor,
            start_date=start_time,
            end_date=end_time,
        )

        self.token = str(AccessToken.for_user(self.user))
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def test_fish_death_notification(self):
        """Test that a notification is created when fish death data is added."""
        response = self.client.post(
            f'/{self.pond.pond_id}/{self.cycle.id}/death/',
            data=json.dumps({'count': 10}),
            content_type="application/json",
            headers=self.headers
        )

        # Check the response
        self.assertEqual(response.status_code, 200)
        self.assertIn("message", response.json())
        self.assertEqual(response.json()["message"], "Fish death data recorded successfully.")

        # Check that a notification was created
        notification = FishDeathNotification.objects.filter(user=self.supervisor).first()
        self.assertIsNotNone(notification)
        self.assertEqual(notification.title, "Fish Death Alert")
        self.assertIn("10 fish deaths reported", notification.message)