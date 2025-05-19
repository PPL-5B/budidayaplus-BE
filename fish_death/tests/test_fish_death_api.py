from unittest.mock import patch, MagicMock
from django.test import TestCase
from ninja.testing import TestClient
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth.models import User
from datetime import datetime, date
from uuid import uuid4

from fish_death.api import router

client = TestClient(router)

class FishDeathAPITest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='tester',
            password='pass1234',
            first_name='Dina',
            last_name='Putri'
        )
        self.token = str(AccessToken.for_user(self.user))
        self.headers = {'Authorization': f'Bearer {self.token}'}
        self.pond_id = str(uuid4())
        self.cycle_id = str(uuid4())

    @patch("fish_death.api.JWTAuth.authenticate")
    @patch("fish_death.api.get_object_or_404")
    @patch("fish_death.api.fish_death_service.create_fish_death")
    def test_create_fish_death_success(self, mock_create, mock_get, mock_auth):
        # Stub JWT auth
        mock_auth.return_value = self.user

        # Stub DB fetches
        mock_get.side_effect = [
            MagicMock(pond_id=self.pond_id),  # Pond
            MagicMock(id=self.cycle_id, start_date=date(2024, 1, 1), end_date=date(2025, 12, 31)),  # Cycle
            self.user  # Reporter
        ]

        # Mock service logic
        mock_create.return_value = MagicMock(
            id=uuid4(),
            pond=MagicMock(pond_id=self.pond_id),
            cycle=MagicMock(id=self.cycle_id),
            reporter=self.user,
            recorded_at=datetime(2025, 5, 18, 10, 0, 0),
            fish_death_count=10,
            fish_alive_count=90,
        )

        payload = {"fish_death_count": 10}
        response = client.post(f"/{self.pond_id}/{self.cycle_id}/", json=payload, headers=self.headers)

        assert response.status_code == 200
        assert response.json()["fish_death_count"] == 10
        assert response.json()["fish_alive_count"] == 90

    @patch("fish_death.api.JWTAuth.authenticate")
    @patch("fish_death.api.get_object_or_404")
    @patch("fish_death.api.fish_death_service.get_latest_fish_death")
    def test_get_latest_fish_death(self, mock_latest, mock_get, mock_auth):
        # Stub JWT
        mock_auth.return_value = self.user

        # Stub model fetch
        mock_get.side_effect = [MagicMock(), MagicMock()]

        mock_latest.return_value = {
            "id": str(uuid4()),
            "pond_id": self.pond_id,
            "cycle_id": self.cycle_id,
            "reporter": {
                "id": self.user.id,
                "username": self.user.username,
                "first_name": self.user.first_name,
                "last_name": self.user.last_name
            },
            "recorded_at": datetime(2025, 5, 18, 10, 0, 0).isoformat(),
            "fish_death_count": 10,
            "fish_alive_count": 90,
        }

        response = client.get(f"/{self.pond_id}/{self.cycle_id}/latest/", headers=self.headers)

        assert response.status_code == 200
        assert response.json()["fish_death_count"] == 10
        assert "reporter" in response.json()

    @patch("fish_death.api.JWTAuth.authenticate")
    @patch("fish_death.api.fish_death_service.list_fish_deaths")
    def test_list_fish_deaths(self, mock_list, mock_auth):
        mock_auth.return_value = self.user

        mock_list.return_value = {
            "cycle_id": self.cycle_id,
            "fish_deaths": [
                {
                    "id": str(uuid4()),
                    "pond_id": self.pond_id,
                    "cycle_id": self.cycle_id,
                    "fish_death_count": 10,
                    "fish_alive_count": 90,
                    "recorded_at": datetime(2025, 5, 18, 10, 0, 0).isoformat(),
                    "reporter": {
                        "id": self.user.id,
                        "username": self.user.username,
                        "first_name": self.user.first_name,
                        "last_name": self.user.last_name
                    }
                }
            ]
        }

        response = client.get(f"/{self.pond_id}/", headers=self.headers)

        assert response.status_code == 200
        assert isinstance(response.json()["fish_deaths"], list)
        assert response.json()["fish_deaths"][0]["fish_death_count"] == 10
    
    @patch("fish_death.api.JWTAuth.authenticate")
    @patch("fish_death.api.get_object_or_404")
    def test_create_fish_death_cycle_not_active(self, mock_get, mock_auth):
        mock_auth.return_value = self.user

        # Simulate an expired cycle (today is outside of this range)
        mock_get.side_effect = [
            MagicMock(pond_id=self.pond_id),  # Pond
            MagicMock(
                id=self.cycle_id,
                start_date=date(2020, 1, 1),
                end_date=date(2020, 12, 31)
            ),
            self.user  # Reporter
        ]

        payload = {"fish_death_count": 10}
        response = client.post(f"/{self.pond_id}/{self.cycle_id}/", json=payload, headers=self.headers)

        assert response.status_code == 400
        assert "Siklus tidak aktif" in response.content.decode()
    

    @patch("fish_death.api.JWTAuth.authenticate")
    @patch("fish_death.api.get_object_or_404")
    def test_create_fish_death_invalid_count(self, mock_get, mock_auth):
        mock_auth.return_value = self.user

        # Active cycle
        mock_get.side_effect = [
            MagicMock(pond_id=self.pond_id),  # Pond
            MagicMock(
                id=self.cycle_id,
                start_date=date(2024, 1, 1),
                end_date=date(2025, 12, 31)
            ),
            self.user  # Reporter
        ]

        payload = {"fish_death_count": -1}  # invalid count
        response = client.post(f"/{self.pond_id}/{self.cycle_id}/", json=payload, headers=self.headers)

        assert response.status_code == 400
        assert "Input jumlah kematian ikan tidak valid" in response.content.decode()