import uuid
import json
from django.test import TestCase
from django.contrib.auth.models import User
from ninja.testing import TestClient
from rest_framework_simplejwt.tokens import AccessToken
from datetime import datetime, timedelta
from django.utils.timezone import make_aware

from pond.models import Pond
from cycle.models import Cycle, PondFishAmount
from fish_death.models import FishDeath
from fish_death.api import router
from user_profile.models import UserProfile, Worker
from fish_death.models import FishDeathNotification 

class FishDeathAPITest(TestCase):
    def setUp(self):
        self.client = TestClient(router)

        # Create a supervisor and its profile
        self.supervisor = User.objects.create_user(username='supervisor', password='password', is_staff=True)
        self.supervisor_profile, _ = UserProfile.objects.get_or_create(user=self.supervisor)

        # Create a worker assigned to the supervisor
        self.user = User.objects.create_user(username='worker', password='password')
        self.worker = Worker.objects.create(user=self.user, assigned_supervisor=self.supervisor_profile)

        # Create a pond (owner is supervisor)
        self.pond = Pond.objects.create(
            owner=self.supervisor,
            name='Test Pond',
            image_name='test_pond.png',
            length=10.0,
            width=5.0,
            depth=2.0
        )

        # Create an active cycle (today is between start_date and end_date)
        today = datetime.now().date()
        self.cycle = Cycle.objects.create(
            supervisor=self.supervisor,
            start_date=today - timedelta(days=1),
            end_date=today + timedelta(days=1)
        )

        # Create an initial fish death record for testing GET latest
        self.fish_death = FishDeath.objects.create(
            pond=self.pond,
            reporter=self.user,
            cycle=self.cycle,
            recorded_at=make_aware(datetime.now()),
            fish_death_count=5,
            fish_alive_count=100
        )

        # Generate a token for authentication
        self.token = str(AccessToken.for_user(self.user))
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def test_create_fish_death(self):
        """
        Test creating a new fish death record.
        The payload only contains fish_death_count; the API should fill in recorded_at and fish_alive_count
        (defaulting to 0 when no PondFishAmount exists).
        """
        url = f'/{self.pond.pond_id}/{self.cycle.id}/'
        payload = {"fish_death_count": 7}
        response = self.client.post(
            url,
            data=json.dumps(payload),
            content_type="application/json",
            headers=self.headers
        )
        self.assertEqual(response.status_code, 200, response.json())
        data = response.json()
        self.assertIn("id", data)
        self.assertEqual(data["fish_death_count"], 7)
        self.assertEqual(data["fish_alive_count"], 0)  # Default value since no PondFishAmount exists
        self.assertEqual(data["pond_id"], str(self.pond.pond_id))
        self.assertEqual(data["cycle_id"], str(self.cycle.id))
        self.assertTrue(data["recorded_at"])

    def test_create_fish_death_invalid_count(self):
        """
        Test creating a fish death record with an invalid fish_death_count (e.g. a negative value).
        The API should return a 400 error.
        """
        url = f'/{self.pond.pond_id}/{self.cycle.id}/'
        payload = {"fish_death_count": -3}
        response = self.client.post(
            url,
            data=json.dumps(payload),
            content_type="application/json",
            headers=self.headers
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("detail", response.json())

    def test_create_fish_death_cycle_not_active(self):
        """
        Test creating a fish death record when the cycle is not active.
        The API should return a 400 error with a message indicating the cycle is inactive.
        """
        # Create a cycle that is not active (end date in the past)
        past_date = datetime.now().date() - timedelta(days=10)
        cycle_inactive = Cycle.objects.create(
            supervisor=self.supervisor,
            start_date=past_date - timedelta(days=5),
            end_date=past_date - timedelta(days=1)
        )
        url = f'/{self.pond.pond_id}/{cycle_inactive.id}/'
        payload = {"fish_death_count": 5}
        response = self.client.post(
            url,
            data=json.dumps(payload),
            content_type="application/json",
            headers=self.headers
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json().get('detail'), "Siklus tidak aktif")

    def test_create_fish_death_with_existing_pond_fish_amount(self):
        """
        Test creating a fish death record when a PondFishAmount record exists.
        The fish_alive_count should be set to the fish_amount from that record.
        """
        pond_fish_amount_value = 150
        PondFishAmount.objects.create(
            pond=self.pond,
            cycle=self.cycle,
            fish_amount=pond_fish_amount_value
        )

        url = f'/{self.pond.pond_id}/{self.cycle.id}/'
        payload = {"fish_death_count": 10}
        response = self.client.post(
            url,
            data=json.dumps(payload),
            content_type="application/json",
            headers=self.headers
        )
        self.assertEqual(response.status_code, 200, response.json())
        data = response.json()
        # Verify that fish_alive_count comes from the PondFishAmount record.
        self.assertEqual(data["fish_alive_count"], pond_fish_amount_value)

    def test_get_latest_fish_death(self):
        """
        Test retrieving the latest fish death record.
        """
        url = f'/{self.pond.pond_id}/{self.cycle.id}/latest/'
        response = self.client.get(url, headers=self.headers)
        self.assertEqual(response.status_code, 200, response.json())
        data = response.json()
        self.assertEqual(data["fish_death_count"], self.fish_death.fish_death_count)
        self.assertEqual(data["pond_id"], str(self.pond.pond_id))
        self.assertEqual(data["cycle_id"], str(self.cycle.id))
        self.assertTrue(data["recorded_at"])

    def test_get_latest_fish_death_no_data(self):
        """
        Test retrieving the latest fish death record when no record exists.
        """
        FishDeath.objects.all().delete()
        url = f'/{self.pond.pond_id}/{self.cycle.id}/latest/'
        response = self.client.get(url, headers=self.headers)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json().get('detail'), 'Data tidak ditemukan')

    def test_get_latest_fish_death_cycle_not_active(self):
        """
        Test retrieving the latest fish death record for a cycle that is not active.
        """
        past_date = datetime.now().date() - timedelta(days=90)
        cycle_inactive = Cycle.objects.create(
            supervisor=self.supervisor,
            start_date=past_date - timedelta(days=10),
            end_date=past_date - timedelta(days=5)
        )
        url = f'/{self.pond.pond_id}/{cycle_inactive.id}/latest/'
        response = self.client.get(url, headers=self.headers)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json().get('detail'), 'Data tidak ditemukan')

    def test_get_fish_death_invalid_pond(self):
        """
        Test GET latest with an invalid pond id.
        """
        invalid_pond_id = str(uuid.uuid4())
        url = f'/{invalid_pond_id}/{self.cycle.id}/latest/'
        response = self.client.get(url, headers=self.headers)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json().get('detail'), 'Not Found')

    def test_list_fish_deaths_unauthorized(self):
        """
        Test listing fish death records without proper authentication.
        """
        url = f'/{self.pond.pond_id}/'
        response = self.client.get(url, headers={})
        self.assertEqual(response.status_code, 401)

    def test_list_fish_deaths(self):
        """
        Test listing fish death records.
        Create an additional record and verify that the list endpoint returns both records.
        """
        # Create an extra fish death record
        FishDeath.objects.create(
            pond=self.pond,
            reporter=self.user,
            cycle=self.cycle,
            recorded_at=make_aware(datetime.now()),
            fish_death_count=8,
            fish_alive_count=90
        )
        url = f'/{self.pond.pond_id}/'
        response = self.client.get(url, headers=self.headers)
        self.assertEqual(response.status_code, 200, response.json())
        data = response.json()
        self.assertIn("fish_deaths", data)
        # Expect at least 2 records (one from setUp and the extra one)
        self.assertGreaterEqual(len(data["fish_deaths"]), 2)
        self.assertEqual(data["cycle_id"], str(self.cycle.id))

        fish_deaths_list = data["fish_deaths"]
        self.assertEqual(len(fish_deaths_list), 2)
        self.assertEqual(fish_deaths_list[0]["id"], str(fd2.id))
        self.assertEqual(fish_deaths_list[1]["id"], str(fd1.id))