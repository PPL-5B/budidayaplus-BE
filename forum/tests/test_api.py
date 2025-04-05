from django.test import TestCase, Client
from django.contrib.auth.models import User
from forum.models import Forum
from django.contrib.auth.models import User, AnonymousUser
import uuid
import json
from forum.repositories.forum_repository import ForumRepository
from ninja_jwt.tokens import RefreshToken

class ForumAPITestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="password123")
        self.user_token = str(RefreshToken.for_user(self.user).access_token)

    def _authenticated_post(self, url, data, token):
        """Helper to make an authenticated POST request with JSON data."""
        return self.client.post(
            url,
            data=json.dumps(data),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}"
        )
    
    def _authenticated_delete(self, url, token):
        """Helper to make an authenticated DELETE request."""
        return self.client.delete(
            url,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}"
        )

    def test_create_forum_success(self):
        """Test creating a forum post successfully."""
        data = {"description": "My first forum post"}
        response = self._authenticated_post("/api/forum/create", data, self.user_token)
        self.assertEqual(response.status_code, 200)
        resp_json = response.json()
        self.assertIn("id", resp_json)
        self.assertIn("user", resp_json)
        self.assertEqual(resp_json["user"]["phone_number"], "testuser")
        self.assertEqual(resp_json["description"], "My first forum post")
        self.assertIsNone(resp_json.get("parent_id"))

    def test_create_forum_unauthenticated(self):
        """Test that creating a forum post without a token returns 401."""
        data = {"description": "No token here"}
        response = self.client.post(
            "/api/forum/create",
            data=json.dumps(data),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 401)

    def test_create_forum_invalid_parent(self):
        """
        Provide a valid UUID that doesn't match any Forum in the DB.
        Expected: 400 with an error message.
        """
        data = {
            "description": "Post with non-existent parent",
            "parent_id": str(uuid.uuid4())
        }
        response = self._authenticated_post("/api/forum/create", data, self.user_token)
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_create_forum_malformed_parent_id(self):
        """
        Provide an invalid parent_id string that cannot be parsed as a UUID.
        Expected: 422 Unprocessable Entity (from Ninja/Pydantic).
        """
        data = {
            "description": "Post with malformed parent ID",
            "parent_id": "not-a-uuid"
        }
        response = self._authenticated_post("/api/forum/create", data, self.user_token)
        self.assertEqual(response.status_code, 422)
        self.assertIn("detail", response.json())

    def test_create_reply_success(self):
        """Test creating a reply to an existing forum post."""
        parent_data = {"description": "Parent forum post"}
        parent_response = self._authenticated_post("/api/forum/create", parent_data, self.user_token)
        self.assertEqual(parent_response.status_code, 200)
        parent_id = parent_response.json()["id"]

        reply_data = {"description": "This is a reply", "parent_id": parent_id}
        reply_response = self._authenticated_post("/api/forum/create_reply", reply_data, self.user_token)
        self.assertEqual(reply_response.status_code, 200)
        reply_json = reply_response.json()
        self.assertIn("id", reply_json)
        self.assertIn("user", reply_json)
        self.assertEqual(reply_json["user"]["phone_number"], "testuser")
        self.assertEqual(reply_json["description"], "This is a reply")

    def test_create_reply_unauthenticated(self):
        """Test creating a reply without providing a token (should return 401)."""
        data = {"description": "Reply with no token", "parent_id": str(uuid.uuid4())}
        response = self.client.post(
            "/api/forum/create_reply",
            data=json.dumps(data),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 401)

    def test_create_reply_no_parent_id(self):
        """Test creating a reply without providing a parent_id (should return 400)."""
        data = {"description": "Reply missing parent ID"}
        response = self._authenticated_post("/api/forum/create_reply", data, self.user_token)
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_create_reply_invalid_parent(self):
        """
        Provide a valid UUID that doesn't match any Forum for the reply.
        Expected: 400 with an error message.
        """
        data = {"description": "Reply to non-existent forum", "parent_id": str(uuid.uuid4())}
        response = self._authenticated_post("/api/forum/create_reply", data, self.user_token)
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_create_reply_malformed_parent_id(self):
        """
        Provide an invalid parent_id string for the reply.
        Expected: 422 Unprocessable Entity.
        """
        data = {"description": "Reply with malformed parent", "parent_id": "bad-uuid"}
        response = self._authenticated_post("/api/forum/create_reply", data, self.user_token)
        self.assertEqual(response.status_code, 422)
        self.assertIn("detail", response.json())

    def test_delete_forum_success(self):
        """
        Test bahwa forum berhasil dihapus ketika request dilakukan oleh user yang membuatnya.
        Expected: 200 OK dan message sukses.
        """
        forum = ForumRepository.create_forum(user=self.user, description="Forum to delete")
        response = self._authenticated_delete(f"/api/forum/delete/{forum.id}", self.user_token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "Forum deleted successfully.")
    
    def test_delete_forum_not_found(self):
        """
        Test menghapus forum dengan UUID yang tidak ada di database.
        Expected: 404 Not Found atau 403 jika valid tapi bukan milik user.
        """
        random_uuid = uuid.uuid4()
        response = self._authenticated_delete(f"/api/forum/delete/{random_uuid}", self.user_token)
        self.assertIn(response.status_code, [404, 403])
        self.assertTrue("error" in response.json() or "detail" in response.json())

    def test_delete_forum_unauthenticated(self):
        """
        Test menghapus forum tanpa autentikasi (tanpa token).
        Expected: 401 Unauthorized.
        """
        forum = ForumRepository.create_forum(user=self.user, description="Forum with no auth")
        response = self.client.delete(f"/api/forum/delete/{forum.id}")
        self.assertEqual(response.status_code, 401)
