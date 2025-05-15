import uuid
import json
from datetime import datetime, timedelta
from django.test import TestCase
from django.utils.timezone import make_aware
from django.contrib.auth.models import User
from ninja.testing import TestClient
from rest_framework_simplejwt.tokens import AccessToken

from pond.models import Pond
from cycle.models import Cycle, PondFishAmount
from fish_death.models import FishDeath
from fish_death.api import router
from user_profile.models import UserProfile, Worker

class FishDeathAPITest(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.now = make_aware(datetime.now())
        self.today = self.now.date()

        # Users and profiles
        self.supervisor = User.objects.create_user(username='supervisor', password='password', is_staff=True)
        self.supervisor_profile, _ = UserProfile.objects.get_or_create(user=self.supervisor)
        self.user = User.objects.create_user(username='worker', password='password')
        self.worker = Worker.objects.create(user=self.user, assigned_supervisor=self.supervisor_profile)

        # Pond and cycle
        self.pond = Pond.objects.create(
            owner=self.supervisor,
            name='Test Pond',
            image_name='test_pond.png',
            length=10.0,
            width=5.0,
            depth=2.0
        )
        self.cycle = Cycle.objects.create(
            supervisor=self.supervisor,
            start_date=self.today - timedelta(days=1),
            end_date=self.today + timedelta(days=1)
        )

        self.fish_death = FishDeath.objects.create(
            pond=self.pond,
            reporter=self.user,
            cycle=self.cycle,
            recorded_at=self.now,
            fish_death_count=5,
            fish_alive_count=100
        )

        self.token = str(AccessToken.for_user(self.user))
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def _make_url(self, pond_id=None, cycle_id=None, suffix=''):
        """Utility method to generate API URL."""
        pond_id = pond_id or self.pond.pond_id
        cycle_id = cycle_id or self.cycle.id
        return f'/{pond_id}/{cycle_id}/{suffix}'

    def test_create_fish_death(self):
        """Should create a new fish death record with default alive count 0 (no PondFishAmount)"""
        url = self._make_url()
        payload = {"fish_death_count": 7}
        response = self.client.post(url, data=json.dumps(payload), content_type="application/json", headers=self.headers)
        self.assertEqual(response.status_code, 200, response.json())
        data = response.json()
        self.assertEqual(data["fish_death_count"], 7)
        self.assertEqual(data["fish_alive_count"], 0)
        self.assertEqual(data["pond_id"], str(self.pond.pond_id))
        self.assertEqual(data["cycle_id"], str(self.cycle.id))
        self.assertTrue(data["recorded_at"])

    def test_create_fish_death_invalid_count(self):
        """Should return 400 if fish_death_count is negative"""
        response = self.client.post(
            self._make_url(),
            data=json.dumps({"fish_death_count": -3}),
            content_type="application/json",
            headers=self.headers
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("detail", response.json())

    def test_create_fish_death_cycle_not_active(self):
        """Should return 400 if cycle is not active"""
        inactive_cycle = Cycle.objects.create(
            supervisor=self.supervisor,
            start_date=self.today - timedelta(days=15),
            end_date=self.today - timedelta(days=10)
        )
        url = self._make_url(cycle_id=inactive_cycle.id)
        response = self.client.post(
            url,
            data=json.dumps({"fish_death_count": 5}),
            content_type="application/json",
            headers=self.headers
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json().get('detail'), "Siklus tidak aktif")

    def test_create_fish_death_with_existing_pond_fish_amount(self):
        """Should use PondFishAmount as fish_alive_count if exists"""
        PondFishAmount.objects.create(
            pond=self.pond,
            cycle=self.cycle,
            fish_amount=150
        )
        url = self._make_url()
        payload = {"fish_death_count": 10}
        response = self.client.post(url, data=json.dumps(payload), content_type="application/json", headers=self.headers)
        self.assertEqual(response.status_code, 200, response.json())
        self.assertEqual(response.json()["fish_alive_count"], 150)

    def test_get_latest_fish_death(self):
        """Should return latest fish death record"""
        response = self.client.get(self._make_url(suffix="latest/"), headers=self.headers)
        self.assertEqual(response.status_code, 200, response.json())
        data = response.json()
        self.assertEqual(data["fish_death_count"], self.fish_death.fish_death_count)
        self.assertEqual(data["pond_id"], str(self.pond.pond_id))
        self.assertEqual(data["cycle_id"], str(self.cycle.id))
        self.assertTrue(data["recorded_at"])

    def test_get_latest_fish_death_no_data(self):
        """Should return 404 if no fish death exists"""
        FishDeath.objects.all().delete()
        response = self.client.get(self._make_url(suffix="latest/"), headers=self.headers)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json().get('detail'), 'Data tidak ditemukan')

    def test_get_latest_fish_death_cycle_not_active(self):
        """Should return 400 if cycle is inactive"""
        inactive_cycle = Cycle.objects.create(
            supervisor=self.supervisor,
            start_date=self.today - timedelta(days=100),
            end_date=self.today - timedelta(days=50)
        )
        url = self._make_url(cycle_id=inactive_cycle.id, suffix="latest/")
        response = self.client.get(url, headers=self.headers)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json().get('detail'), 'Data tidak ditemukan')

    def test_get_fish_death_invalid_pond(self):
        """Should return 404 if pond id does not exist"""
        invalid_pond_id = str(uuid.uuid4())
        url = self._make_url(pond_id=invalid_pond_id, suffix="latest/")
        response = self.client.get(url, headers=self.headers)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json().get('detail'), 'Not Found')

    def test_list_fish_deaths_unauthorized(self):
        """Should return 401 when no token is provided"""
        url = f'/{self.pond.pond_id}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 401)

    def test_list_fish_deaths(self):
        """Should return list of fish death records"""
        FishDeath.objects.create(
            pond=self.pond,
            reporter=self.user,
            cycle=self.cycle,
            recorded_at=self.now,
            fish_death_count=8,
            fish_alive_count=90
        )
        url = f'/{self.pond.pond_id}/'
        response = self.client.get(url, headers=self.headers)
        self.assertEqual(response.status_code, 200, response.json())
        data = response.json()
        self.assertIn("fish_deaths", data)
        self.assertGreaterEqual(len(data["fish_deaths"]), 2)
        self.assertEqual(data["cycle_id"], str(self.cycle.id))
