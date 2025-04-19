# test_api.py
from unittest.mock import patch
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.contrib.auth.models import User
import uuid
import json
from forum.repositories.forum_repository import ForumRepository
from ninja_jwt.tokens import RefreshToken
from datetime import timedelta
from django.utils import timezone

class ForumAPITestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="password123")
        self.other_user = User.objects.create_user(username="otheruser", password="password123")
        self.forum = Forum.objects.create(user=self.user, description="Original Post")
        self.forum_id = str(self.forum.id)

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
        Expected: 404 Not Found.
        """
        random_uuid = uuid.uuid4()  # UUID yang tidak ada di DB
        response = self._authenticated_delete(f"/api/forum/delete/{random_uuid}", self.user_token)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"], "Not Found.")


    def test_delete_forum_not_owned(self):
        """
        Test menghapus forum yang dibuat oleh user lain.
        Expected: 403 Forbidden.
        """
        # Buat user lain
        other_user = User.objects.create_user(username="lain", password="test1234")
        forum = ForumRepository.create_forum(user=other_user, description="Not yours")
        
        response = self._authenticated_delete(f"/api/forum/delete/{forum.id}", self.user_token)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"], "You are not authorized to delete this forum.")


    def test_delete_forum_unauthenticated(self):
        """
        Test menghapus forum tanpa autentikasi (tanpa token).
        Expected: 401 Unauthorized.
        """
        forum = ForumRepository.create_forum(user=self.user, description="Forum with no auth")
        response = self.client.delete(f"/api/forum/delete/{forum.id}")
        self.assertEqual(response.status_code, 401)

    def _authenticated_get(self, url, token):
        """Helper to make an authenticated GET request."""
        return self.client.get(
            url,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}"
        )

    def test_get_forum_by_id_success(self):
        """Test retrieving a forum by its ID."""
        forum = ForumRepository.create_forum(user=self.user, description="Test forum")
        response = self._authenticated_get(f"/api/forum/get_by_id/{forum.id}", self.user_token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["description"], "Test forum")

    def test_get_forum_by_id_not_found(self):
        """Test retrieving a forum with a non-existent ID."""
        response = self._authenticated_get(f"/api/forum/get_by_id/{uuid.uuid4()}", self.user_token)
        self.assertEqual(response.status_code, 404)
        self.assertIn("error", response.json())

    def test_list_forums_success(self):
        """Test retrieving a list of all forums."""
        ForumRepository.create_forum(user=self.user, description="Forum 1")
        ForumRepository.create_forum(user=self.user, description="Forum 2")
        response = self._authenticated_get("/api/forum/list", self.user_token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 2)

    def test_get_forums_by_user_success(self):
        """Test retrieving forums created by the authenticated user."""
        ForumRepository.create_forum(user=self.user, description="User's forum")
        another_user = User.objects.create_user(username="anotheruser", password="password123")
        ForumRepository.create_forum(user=another_user, description="Another user's forum")
        response = self._authenticated_get("/api/forum/get_by_user", self.user_token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["description"], "User's forum")

    def test_get_forums_by_user_unauthenticated(self):
        """Test retrieving forums by user without authentication."""
        response = self.client.get("/api/forum/get_by_user")
        self.assertEqual(response.status_code, 401)

    def test_get_latest_forum_success(self):
        """Test retrieving the latest forum."""
        old_forum = ForumRepository.create_forum(user=self.user, description="Old forum")
        old_forum.timestamp = timezone.now() - timedelta(days=1) 
        old_forum.save()

        latest_forum = ForumRepository.create_forum(user=self.user, description="Latest forum")
        latest_forum.timestamp = timezone.now() 
        latest_forum.save()

        response = self._authenticated_get("/api/forum/get_latest", self.user_token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["description"], "Latest forum")

    def test_get_latest_forum_not_found(self):
        """Test retrieving the latest forum when no forums exist."""
        response = self._authenticated_get("/api/forum/get_latest", self.user_token)
        self.assertEqual(response.status_code, 404)
        self.assertIn("error", response.json())

    def test_get_replies_success(self):
        """Test retrieving replies for a forum."""
        parent_forum = ForumRepository.create_forum(user=self.user, description="Parent forum")
        ForumRepository.create_forum(user=self.user, description="Reply 1", parent=parent_forum)
        ForumRepository.create_forum(user=self.user, description="Reply 2", parent=parent_forum)
        response = self._authenticated_get(f"/api/forum/get_replies/{parent_forum.id}", self.user_token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 2)


    def test_get_replies_forum_not_found(self):
        """Test retrieving replies for a non-existent forum."""
        response = self._authenticated_get(f"/api/forum/get_replies/{uuid.uuid4()}", self.user_token)
        self.assertEqual(response.status_code, 404)
        self.assertIn("error", response.json())

    def test_create_post_with_invalid_parent_forum(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")
        data = {"description": "This is a test forum post.", "parent_id": str(uuid.uuid4())}  # Random UUID
        response = self.client.post(self.url, data, content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "Invalid parent forum ID"})

    def test_update_forum_success_flow(self):
        """Test full successful update flow including the repository update"""
        # Setup
        forum = Forum.objects.create(user=self.user, description="Original Post")
        update_data = {"description": "Successfully updated description"}
        
        # Action
        response = self._authenticated_put(
            f"/api/forum/{forum.id}/",
            update_data,
            self.user_token
        )
        
        # Assert
        self.assertEqual(response.status_code, 200)
        updated_forum = Forum.objects.get(id=forum.id)
        self.assertEqual(updated_forum.description, "Successfully updated description")
        self.assertEqual(response.json()["description"], "Successfully updated description")

    def test_update_forum_successful_update(self):
        """Test successful forum update including repository call"""
        # Create initial forum
        forum = Forum.objects.create(
            user=self.user,
            description="Original description"
        )
        
        # Update data
        update_data = {
            "description": "Updated description"
        }
        
        # Make the request
        response = self._authenticated_put(
            f"/api/forum/{forum.id}/",
            update_data,
            self.user_token
        )
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["description"], "Updated description")
        
        # Verify the database was actually updated
        updated_forum = Forum.objects.get(id=forum.id)
        self.assertEqual(updated_forum.description, "Updated description")

    @patch('forum.repositories.forum_repository.ForumRepository.update_forum')
    def test_update_forum_repository_called(self, mock_update):
        """Test that repository update method is called"""
        # Setup mock
        mock_update.return_value = Forum(
            id=self.forum.id,
            user=self.user,
            description="Mocked updated description"
        )
        
        # Test data
        update_data = {
            "description": "Should be mocked"
        }
        
        # Make request
        response = self._authenticated_put(
            f"/api/forum/{self.forum.id}/",
            update_data,
            self.user_token
        )
        
        # Verify mock was called
        mock_update.assert_called_once_with(self.forum.id, "Should be mocked")
        
        # Verify response uses mocked data
        self.assertEqual(response.json()["description"], "Mocked updated description")

    def test_update_forum_empty_description(self):
        """Test updating with empty description"""
        forum = Forum.objects.create(
            user=self.user,
            description="Original description"
        )
        
        update_data = {
            "description": ""  # Empty string
        }
        
        response = self._authenticated_put(
            f"/api/forum/{forum.id}/",
            update_data,
            self.user_token
        )
        
        # Should either be 200 (if allowed) or 400 (if validation fails)
        self.assertIn(response.status_code, [200, 400])
        if response.status_code == 200:
            self.assertEqual(Forum.objects.get(id=forum.id).description, "")

    def test_update_forum_return_value_structure(self):
        """Test the returned value has correct structure"""
        forum = Forum.objects.create(
            user=self.user,
            description="Original"
        )
        
        update_data = {
            "description": "New description"
        }
        
        response = self._authenticated_put(
            f"/api/forum/{forum.id}/",
            update_data,
            self.user_token
        )
        
        # Check response structure
        response_data = response.json()
        self.assertIn("id", response_data)
        self.assertIn("description", response_data)
        self.assertIn("user", response_data)
        self.assertIn("created_at", response_data)
        self.assertIn("parent", response_data)