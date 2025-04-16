from unittest.mock import patch
from django.test import TestCase, Client
import os
from django.contrib.auth.models import User
from django.contrib.auth.models import User
import uuid
import json
from forum.models import Forum, ForumVote
from forum.repositories.forum_repository import ForumRepository
from ninja_jwt.tokens import RefreshToken
from datetime import timedelta
from django.utils import timezone

class ForumAPITestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.test_password = os.getenv("TEST_USER_PASSWORD", "defaultpass123")
        
        self.user = User.objects.create_user(username="testuser", password=self.test_password)
        self.other_user = User.objects.create_user(username="otheruser", password=self.test_password)
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
    
    def _authenticated_put(self, url, data, token):
        return self.client.put(
            url,
            data=json.dumps(data),
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
        other_user = User.objects.create_user(username="lain", password=self.test_password)
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
        Forum.objects.all().delete()
        ForumRepository.create_forum(user=self.user, description="Forum 1")
        ForumRepository.create_forum(user=self.user, description="Forum 2")
        response = self._authenticated_get("/api/forum/list", self.user_token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 2)

    def test_get_forums_by_user_success(self):
        Forum.objects.all().delete()  
        ForumRepository.create_forum(user=self.user, description="User's forum")
        another_user = User.objects.create_user(username="anotheruser", password=self.test_password)
        ForumRepository.create_forum(user=another_user, description="Another user's forum")
        response = self._authenticated_get("/api/forum/get_by_user", self.user_token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["description"], "User's forum")


    def test_get_latest_forum_success(self):
        """Test retrieving the latest forum."""
        Forum.objects.all().delete()

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
        Forum.objects.all().delete()  
        response = self._authenticated_get("/api/forum/get_latest", self.user_token)
        self.assertEqual(response.status_code, 404)
        self.assertIn("error", response.json())


    def test_get_replies_forum_not_found(self):
        """Test retrieving replies for a non-existent forum."""
        response = self._authenticated_get(f"/api/forum/get_replies/{uuid.uuid4()}", self.user_token)
        self.assertEqual(response.status_code, 404)
        self.assertIn("error", response.json())
    
    def test_create_post_with_invalid_parent_forum(self):
        data = {
            "description": "This is a test forum post.",
            "parent_id": str(uuid.uuid4())  # Random UUID
        }
        response = self._authenticated_post("/api/forum/create", data, self.user_token)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "Invalid parent forum ID"})

    def test_upvote_success(self):
        response = self._authenticated_post(f"/api/forum/upvote/{self.forum_id}", {}, self.user_token)
        self.assertEqual(response.status_code, 204)

        vote = ForumVote.objects.get(user=self.user, forum=self.forum)
        self.assertEqual(vote.vote_choice, 'up')

    def test_downvote_success(self):
        response = self._authenticated_post(f"/api/forum/downvote/{self.forum_id}", {}, self.user_token)
        self.assertEqual(response.status_code, 204)

        vote = ForumVote.objects.get(user=self.user, forum=self.forum)
        self.assertEqual(vote.vote_choice, 'down')

    def test_change_vote(self):
        self._authenticated_post(f"/api/forum/upvote/{self.forum_id}", {}, self.user_token)
        self._authenticated_post(f"/api/forum/downvote/{self.forum_id}", {}, self.user_token)
    
        vote = ForumVote.objects.get(user=self.user, forum=self.forum)
        self.assertEqual(vote.vote_choice, 'down')
        self.assertEqual(ForumVote.objects.count(), 1) 

    def test_cancel_vote_success(self):
        self._authenticated_post(f"/api/forum/upvote/{self.forum_id}", {}, self.user_token)
        response = self._authenticated_delete(f"/api/forum/cancel_vote/{self.forum_id}", self.user_token)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(ForumVote.objects.filter(user=self.user, forum=self.forum).exists())

    def test_cancel_non_existing_vote(self):
        response = self._authenticated_delete(f"/api/forum/cancel_vote/{self.forum_id}", self.user_token)
        self.assertEqual(response.status_code, 204) 

    def test_vote_on_nonexistent_forum(self):
        non_existent_id = uuid.uuid4()
        response = self._authenticated_post(f"/api/forum/upvote/{non_existent_id}", {}, self.user_token)
        self.assertEqual(response.status_code, 404)

    def test_vote_summary_multiple_users(self):
        self._authenticated_post(f"/api/forum/upvote/{self.forum_id}", {}, self.user_token)
        
        other_token = str(RefreshToken.for_user(self.other_user).access_token)
        self._authenticated_post(f"/api/forum/downvote/{self.forum_id}", {}, other_token)
        
        response = self._authenticated_get(f"/api/forum/vote_summary/{self.forum_id}", self.user_token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["upvotes"], 1)
        self.assertEqual(response.json()["downvotes"], 1)
        self.assertEqual(response.json()["user_vote"], 'up')

    def test_vote_summary_no_votes(self):
        response = self._authenticated_get(f"/api/forum/vote_summary/{self.forum_id}", self.user_token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["upvotes"], 0)
        self.assertEqual(response.json()["downvotes"], 0)
        self.assertIsNone(response.json()["user_vote"])

    def test_vote_unauthenticated(self):
        response = self.client.post(f"/api/forum/upvote/{self.forum_id}")
        self.assertEqual(response.status_code, 401)
        
        response = self.client.post(f"/api/forum/downvote/{self.forum_id}")
        self.assertEqual(response.status_code, 401)
        
        response = self.client.delete(f"/api/forum/cancel_vote/{self.forum_id}")
        self.assertEqual(response.status_code, 401)
    
    def test_vote_summary_success(self):
        self._authenticated_post(f"/api/forum/upvote/{self.forum_id}", {}, self.user_token)
        response = self._authenticated_get(f"/api/forum/vote_summary/{self.forum_id}", self.user_token)
        self.assertEqual(response.status_code, 200)
        self.assertIn("upvotes", response.json())
        self.assertIn("downvotes", response.json())
        self.assertEqual(response.json()["user_vote"], "up")

    def test_vote_summary_unauthenticated(self):
        response = self.client.get(f"/api/forum/vote_summary/{self.forum_id}")
        self.assertEqual(response.status_code, 401)

    def test_update_forum_not_found(self):
        update_data = {"description": "Does not exist"}
        response = self._authenticated_put(f"/api/forum/{uuid.uuid4()}/", update_data, self.user_token)
        self.assertEqual(response.status_code, 404)
    
    def test_get_replies_success(self):
        """Test retrieving replies for a forum."""
        parent_forum = ForumRepository.create_forum(user=self.user, description="Parent forum")
        ForumRepository.create_forum(user=self.user, description="Reply 1", parent=parent_forum)
        ForumRepository.create_forum(user=self.user, description="Reply 2", parent=parent_forum)
        response = self._authenticated_get(f"/api/forum/get_replies/{parent_forum.id}", self.user_token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 2)
    
    def test_update_forum_success(self):
        """Test successful forum update by owner"""
        forum = ForumRepository.create_forum(
            user=self.user,
            description="Original description"
        )
        update_data = {"description": "Updated description"}
        response = self._authenticated_put(
            f"/api/forum/{forum.id}",
            update_data,
            self.user_token
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["description"], "Updated description")
        
        updated_forum = Forum.objects.get(id=forum.id)
        self.assertEqual(updated_forum.description, "Updated description")

    def test_update_forum_unauthenticated(self):
        """Test updating forum without authentication"""
        forum = ForumRepository.create_forum(
            user=self.user,
            description="Original post"
        )
        update_data = {"description": "Unauthenticated update"}
        response = self.client.put(
            f"/api/forum/{forum.id}",
            data=json.dumps(update_data),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 401)

    def test_update_forum_invalid_data(self):
        """Test updating with invalid data (empty description)"""
        forum = ForumRepository.create_forum(
            user=self.user,
            description="Original post"
        )
        update_data = {"description": ""}  
        response = self._authenticated_put(
            f"/api/forum/{forum.id}",
            update_data,
            self.user_token
        )
        self.assertEqual(response.status_code, 422) 
        self.assertIn("detail", response.json())
    
    def test_update_forum_forbidden_not_owner(self):
        """Test user lain tidak bisa update forum"""
        other_forum = ForumRepository.create_forum(
            user=self.other_user,
            description="Post user lain"
        )
        
        update_data = {"description": "Coba ubah punya orang"}
        
        response = self._authenticated_put(
            f"/api/forum/{other_forum.id}",
            update_data,
            self.user_token
        )
        
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json()["error"],
            "You are not authorized to update this forum post."
        )
        
        unchanged_forum = Forum.objects.get(id=other_forum.id)
        self.assertEqual(unchanged_forum.description, "Post user lain")
    
    def test_update_forum_not_found(self):
        """Test update forum dengan ID yang tidak ada"""
        non_existent_id = uuid.uuid4()
        update_data = {"description": "Coba update forum tidak ada"}
        
        response = self._authenticated_put(
            f"/api/forum/{non_existent_id}",
            update_data,
            self.user_token
        )
        
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"], "Forum not found")
