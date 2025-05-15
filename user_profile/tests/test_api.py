import json
from django.test import TestCase
from django.contrib.auth.models import User
from ninja_jwt.tokens import RefreshToken
from rest_framework.test import APIClient
from user_profile.models import UserProfile, Worker
from unittest.mock import patch
from django.core.exceptions import PermissionDenied

class UserProfileApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.supervisor_user = User.objects.create_user(username="supervisor", password="password", is_staff=True)
        self.supervisor_profile = UserProfile.objects.get(user=self.supervisor_user)  # created by signal

        self.regular_user = User.objects.create_user(username="user1", password="password")
        self.regular_profile = UserProfile.objects.create(user=self.regular_user)

        self.worker_user = User.objects.create_user(username="worker1", password="password")
        self.worker = Worker.objects.create(user=self.worker_user, assigned_supervisor=self.supervisor_profile)
        self.worker_profile = UserProfile.objects.get(user=self.worker_user)

        token = str(RefreshToken.for_user(self.supervisor_user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_update_profile(self):
        data = {"first_name": "NewFirst", "last_name": "NewLast", "image_name": "img.png"}
        res = self.client.put("/api/user-profile/", data, format="json")
        self.assertEqual(res.status_code, 200)
        body = json.loads(res.content)
        self.assertEqual(body["first_name"], "NewFirst")

    def test_get_profile_by_username(self):
        res = self.client.get(f"/api/user-profile/{self.regular_user.username}/")
        self.assertEqual(res.status_code, 200)
        body = json.loads(res.content)
        self.assertEqual(body["user"]["phone_number"], "user1")

    def test_get_profile_by_user(self):
        res = self.client.get("/api/user-profile/")
        self.assertEqual(res.status_code, 200)
        body = json.loads(res.content)
        self.assertEqual(body["user"]["phone_number"], "supervisor")

    def test_get_team(self):
        res = self.client.get("/api/user-profile/team")
        self.assertEqual(res.status_code, 200)
        body = json.loads(res.content)
        self.assertTrue(any(p["id"] == str(self.worker_profile.id) for p in body))

    def test_get_team_by_username(self):
        res = self.client.get(f"/api/user-profile/team/{self.supervisor_user.username}")
        self.assertEqual(res.status_code, 200)
        body = json.loads(res.content)
        self.assertTrue(any(p["id"] == str(self.worker_profile.id) for p in body))

    def test_get_workers_only(self):
        res = self.client.get("/api/user-profile/workers-only")
        self.assertEqual(res.status_code, 200)
        body = json.loads(res.content)
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["id"], str(self.worker_profile.id))

    def test_is_in_team_true(self):
        token = str(RefreshToken.for_user(self.worker_user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        res = self.client.get(f"/api/user-profile/is-in-team/{self.supervisor_user.username}")
        self.assertEqual(res.status_code, 200)
        body = json.loads(res.content)
        self.assertTrue(body)

    def test_is_in_team_false(self):
        token = str(RefreshToken.for_user(self.regular_user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        res = self.client.get(f"/api/user-profile/is-in-team/{self.supervisor_user.username}")
        self.assertEqual(res.status_code, 200)
        body = json.loads(res.content)
        self.assertFalse(body)

    def test_is_supervisor(self):
        res = self.client.get(f"/api/user-profile/is-supervisor/{self.supervisor_user.username}")
        self.assertEqual(res.status_code, 200)
        body = json.loads(res.content)
        self.assertTrue(body)

    def test_create_worker(self):
        payload = {
            "phone_number": "089999999999",
            "first_name": "Worker",
            "last_name": "Baru",
            "password": "password123",
        }
        res = self.client.post("/api/user-profile/create-worker", payload, format="json")
        self.assertEqual(res.status_code, 200)
        body = json.loads(res.content)
        self.assertEqual(body["user"]["phone_number"], "089999999999")

    def test_create_worker_with_existing_phone(self):
        payload = {
            "phone_number": self.worker_user.username,
            "first_name": "Worker",
            "last_name": "Baru",
            "password": "password123",
        }
        res = self.client.post("/api/user-profile/create-worker", payload, format="json")
        self.assertEqual(res.status_code, 400)
        body = json.loads(res.content)
        self.assertIn("Nomor telefon sudah digunakan", body["detail"])
    
    def test_create_worker_by_non_supervisor(self):
        # Login sebagai user biasa, bukan staff
        token = str(RefreshToken.for_user(self.regular_user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        payload = {
            "phone_number": "088888888888",
            "first_name": "NotAllowed",
            "last_name": "User",
            "password": "somepass123",
        }
        res = self.client.post("/api/user-profile/create-worker", payload, format="json")
        self.assertEqual(res.status_code, 403)
        body = json.loads(res.content)
        self.assertIn("Anda tidak memiliki akses", body["detail"])
    
    def test_profile_not_found(self):
        # Buat user tanpa UserProfile (bukan staff, tanpa sinyal)
        orphan_user = User.objects.create_user(username="no_profile_user", password="1234")
        token = str(RefreshToken.for_user(orphan_user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        res = self.client.get("/api/user-profile/")
        self.assertEqual(res.status_code, 404)
        body = json.loads(res.content)
        self.assertIn("Profile tidak ditemukan", body["detail"])
    
    def test_handle_exceptions_permission_denied(self):
        token = str(RefreshToken.for_user(self.supervisor_user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        # Patch fungsi GetTeamServiceImpl.get_team agar melempar PermissionDenied
        with patch("user_profile.services.get_team_service_impl.GetTeamServiceImpl.get_team") as mock_get_team:
            mock_get_team.side_effect = PermissionDenied("Anda tidak memiliki akses")

            res = self.client.get("/api/user-profile/team")
            self.assertEqual(res.status_code, 403)
            body = json.loads(res.content)
            self.assertEqual(body["detail"], "Anda tidak memiliki akses untuk melakukan ini")

    def test_get_profile_by_username_unexpected_error(self):
        with patch("user_profile.services.retrieve_service_impl.RetrieveServiceImpl.retrieve_profile", side_effect=Exception("Test Error")):
            res = self.client.get(f"/api/user-profile/{self.regular_user.username}/")
            self.assertEqual(res.status_code, 400)
            body = json.loads(res.content)
            self.assertIn("Test Error", body["detail"])
    
    @patch("django.contrib.auth.models.User.objects.create_user", side_effect=Exception("Unexpected Create Error"))
    def test_create_worker_generic_exception(self, mocked_create_user):
        payload = {
            "phone_number": "081111111111",
            "first_name": "X",
            "last_name": "Y",
            "password": "12345678"
        }
        res = self.client.post("/api/user-profile/create-worker", payload, format="json")
        self.assertEqual(res.status_code, 400)
        body = json.loads(res.content)
        self.assertIn("Unexpected Create Error", body["detail"])





