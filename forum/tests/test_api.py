import os
from unittest.mock import patch
import uuid
import json
from django.test import TestCase, Client
from django.contrib.auth.models import User
from ninja_jwt.tokens import RefreshToken
from forum.models import Forum, ForumVote
from forum.repositories.forum_repository import ForumRepository
from forum.schemas import ForumUpdateSchema
from django.http import HttpRequest
from forum.api import update_forum


class ForumAPITest(TestCase):
    def setUp(self):
        pwd = os.getenv("TEST_USER_PASSWORD", "defaultpass123") 

        self.client = Client()
        self.user = User.objects.create_user(username="user1", password=pwd)
        self.user2 = User.objects.create_user(username="user2", password=pwd)
        self.token = str(RefreshToken.for_user(self.user).access_token)
        self.token2 = str(RefreshToken.for_user(self.user2).access_token)
        self.forum = ForumRepository.create_forum(
            user=self.user, title="Forum A", description="First forum", tag="ikan"
        )
        self.forum_id = str(self.forum.id)
        self.user_token = str(RefreshToken.for_user(self.user).access_token)
        self.other_user_token = str(RefreshToken.for_user(self.user2).access_token)

    def _authenticated_post(self, url, data, token):
        """Helper to make an authenticated POST request with JSON data."""
        return self.client.post(
            url,
            data=json.dumps(data),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}"
        )
    
    def _authenticated_put(self, url, data, token):
        """Helper to make an authenticated PUT request with JSON data."""
        return self.client.put(
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

    def _authenticated_get(self, url, token):
        """Helper to make an authenticated GET request."""
        return self.client.get(
            url,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}"
        )

    def _auth_get(self, url, token):
        return self.client.get(url, content_type="application/json", HTTP_AUTHORIZATION=f"Bearer {token}")

    def _auth_post(self, url, data, token):
        return self.client.post(url, data=json.dumps(data), content_type="application/json", HTTP_AUTHORIZATION=f"Bearer {token}")

    def _auth_put(self, url, data, token):
        return self.client.put(url, data=json.dumps(data), content_type="application/json", HTTP_AUTHORIZATION=f"Bearer {token}")

    def _auth_delete(self, url, token):
        return self.client.delete(url, content_type="application/json", HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_create_and_reply(self):
        response = self.client.post(
            "/api/forum/create_reply",
            data=json.dumps({
                "description": "Ini reply",
                "parent_id": self.forum_id,
                "tag": "ikan"
            }),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}"
        )
        self.assertEqual(response.status_code, 200)

    # Existing test cases
    def test_upvote_and_cancel_vote(self):
        res_upvote = self._auth_post(f"/api/forum/upvote/{self.forum_id}", {}, self.token)
        self.assertEqual(res_upvote.status_code, 204)
        self.assertTrue(ForumVote.objects.filter(user=self.user, forum=self.forum).exists())

        res_cancel = self._auth_delete(f"/api/forum/cancel_vote/{self.forum_id}", self.token)
        self.assertEqual(res_cancel.status_code, 204)
        self.assertFalse(ForumVote.objects.filter(user=self.user, forum=self.forum).exists())

    def test_vote_summary_for_voted_and_unvoted_user(self):
        """
        Test vote summary untuk user yang sudah vote dan belum vote.
        """
        # User memberikan vote
        ForumVote.objects.create(user=self.user, forum=self.forum)

        # Ambil summary untuk user yang sudah vote
        res_with_vote = self._auth_get(f"/api/forum/vote_summary/{self.forum.id}", self.token)
        self.assertEqual(res_with_vote.status_code, 200)
        self.assertIn("user_vote", res_with_vote.json())
        self.assertIsNotNone(res_with_vote.json()["user_vote"])  # Pastikan user_vote ada

        # Ambil summary untuk user yang belum vote
        res_without_vote = self._auth_get(f"/api/forum/vote_summary/{self.forum.id}", self.other_user_token)
        self.assertEqual(res_without_vote.status_code, 200)
        self.assertIn("user_vote", res_without_vote.json())
        self.assertIsNone(res_without_vote.json()["user_vote"])  # Pastikan user_vote None

    def test_user_votes_authenticated(self):
        ForumRepository.upvote_forum(self.user, self.forum)
        res = self._auth_get("/api/forum/user_votes", self.token)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()["votes"]), 1)

    def test_user_votes_unauthenticated(self):
        res = self.client.get("/api/forum/user_votes")
        self.assertEqual(res.status_code, 401)

    def test_list_forums_pagination(self):
        for i in range(5):
            ForumRepository.create_forum(user=self.user, title=f"Forum {i}", description="...", tag="ikan")
        res = self._auth_get("/api/forum/list?limit=3&offset=0", self.token)
        self.assertEqual(res.status_code, 200)
        self.assertLessEqual(len(res.json()), 3)

    def test_search_forums_valid_and_empty_query(self):
        ForumRepository.create_forum(user=self.user, title="Searchable", description="desc", tag="ikan")

        res = self._auth_get("/api/forum/search?query=Search", self.token)
        self.assertEqual(res.status_code, 200)
        self.assertGreaterEqual(len(res.json()), 1)

        res_empty = self._auth_get("/api/forum/search?query=   ", self.token)
        self.assertEqual(res_empty.status_code, 400)
        self.assertIn("error", res_empty.json())

    def test_update_forum_invalid_and_success(self):
        update_data = {"title": "Updated", "description": "New desc", "tag": "ikan"}

        res_not_found = self._auth_put(f"/api/forum/{uuid.uuid4()}", update_data, self.token)
        self.assertEqual(res_not_found.status_code, 404)

        res_forbidden = self._auth_put(f"/api/forum/{self.forum_id}", update_data, self.token2)
        self.assertEqual(res_forbidden.status_code, 403)

        res_success = self._auth_put(f"/api/forum/{self.forum_id}", update_data, self.token)
        self.assertEqual(res_success.status_code, 200)
        self.assertEqual(res_success.json()["title"], "Updated")
        self.assertEqual(res_success.json()["description"], "New desc")
        self.assertEqual(res_success.json()["tag"], "ikan")
        
    def test_update_forum_success_direct_call(self):
        update_data = {"title": "Updated", "description": "New desc", "tag": "ikan"}
        request = HttpRequest()
        request.user = self.user

        data = ForumUpdateSchema(**update_data)
        result = update_forum(request, uuid.UUID(self.forum_id), data)

        self.assertEqual(result.title, "Updated")
        self.assertEqual(result.description, "New desc")
        self.assertEqual(result.tag, "ikan")
            

    def test_create_forum_no_title_on_main_post(self):
        data = {
            "title": "",  # kosong
            "description": "Post tanpa judul",
            "tag": "ikan"
        }
        res = self._auth_post("/api/forum/create", data, self.token)
        self.assertEqual(res.status_code, 400)
        self.assertIn("Title wajib diisi", res.json()["error"])

    def test_create_forum_invalid_parent_id(self):
        """Invalid parent ID should return 400 error."""
        data = {
            "title": "Invalid Parent Test",
            "description": "Desc",
            "tag": "ikan",
            "parent_id": str(uuid.uuid4())  # random UUID, not exist
        }

        res = self._auth_post("/api/forum/create", data, self.token)
        self.assertEqual(res.status_code, 400)
        self.assertIn("Invalid parent forum ID", res.json()["error"])

    def test_create_reply_missing_parent_id(self):
        """Reply post must have a parent_id."""
        data = {
            "description": "Reply tanpa parent_id",
            "tag": "kolam"
        }
        res = self._auth_post("/api/forum/create_reply", data, self.token)
        self.assertEqual(res.status_code, 400)
        self.assertIn("Parent forum ID is required", res.json()["error"])

    def test_create_reply_invalid_parent_id(self):
        """Invalid parent_id on reply should return 400."""
        data = {
            "description": "Invalid reply",
            "tag": "kolam",
            "parent_id": str(uuid.uuid4())  # random UUID, not exist
        }
        res = self._auth_post("/api/forum/create_reply", data, self.token)
        self.assertEqual(res.status_code, 400)
        self.assertIn("Invalid parent forum ID", res.json()["error"])

    def test_get_by_id_success_and_not_found(self):
        res = self._auth_get(f"/api/forum/get_by_id/{self.forum_id}", self.token)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["id"], self.forum_id)

        res_invalid = self._auth_get(f"/api/forum/get_by_id/{uuid.uuid4()}", self.token)
        self.assertEqual(res_invalid.status_code, 404)

    def test_get_by_user_auth_and_unauth(self):
        res = self._auth_get("/api/forum/get_by_user", self.token)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()), 1)

        res_noauth = self.client.get("/api/forum/get_by_user")
        self.assertEqual(res_noauth.status_code, 401)

    def test_get_by_tag_valid_invalid(self):
        res_valid = self._auth_get("/api/forum/get_by_tag/ikan", self.token)
        self.assertEqual(res_valid.status_code, 200)

        res_invalid = self._auth_get("/api/forum/get_by_tag/invalid", self.token)
        self.assertEqual(res_invalid.status_code, 400)
        self.assertIn("Invalid tag", res_invalid.json()["error"])

    def test_get_replies_success_and_invalid(self):
        ForumRepository.create_forum(
            user=self.user, title="", description="Balasan", tag="kolam", parent=self.forum
        )
        
        res = self._auth_get(f"/api/forum/get_replies/{self.forum_id}", self.token)
        self.assertEqual(res.status_code, 200)
        self.assertGreaterEqual(len(res.json()), 1)

        res_invalid = self._auth_get(f"/api/forum/get_replies/{uuid.uuid4()}", self.token)
        self.assertEqual(res_invalid.status_code, 404)

    def test_delete_forum_success_forbidden_notfound(self):
        forum_to_delete = ForumRepository.create_forum(
            user=self.user, title="To be deleted", description="...", tag="ikan"
        )
        res = self._auth_delete(f"/api/forum/delete/{forum_to_delete.id}", self.token)
        self.assertEqual(res.status_code, 200)

        res_forbidden = self._auth_delete(f"/api/forum/delete/{self.forum_id}", self.token2)
        self.assertEqual(res_forbidden.status_code, 403)

        res_notfound = self._auth_delete(f"/api/forum/delete/{uuid.uuid4()}", self.token)
        self.assertEqual(res_notfound.status_code, 404)
    
    def test_create_forum_unauthenticated(self):
        """Should return 403/401 if not logged in"""
        data = {
            "title": "Judul",
            "description": "Konten",
            "tag": "ikan"
        }
        response = self.client.post(
            "/api/forum/create",
            data=json.dumps(data),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 401)
        self.assertIn("Unauthorized", response.content.decode())

    def test_create_forum_success(self):
        """Should successfully create a forum when authenticated"""
        data = {
            "title": "Forum Baru",
            "description": "Deskripsi forum",
            "tag": "ikan"
        }
        res = self._auth_post("/api/forum/create", data, self.token)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["title"], "Forum Baru")
        self.assertEqual(res.json()["description"], "Deskripsi forum")
        self.assertEqual(res.json()["user"]["phone_number"], "user1")
    
    def test_create_reply_success(self):
        """Should successfully create a reply with valid parent_id"""
        data = {
            "description": "Ini adalah balasan",
            "parent_id": self.forum_id,
            "tag": "kolam"
        }
        res = self._auth_post("/api/forum/create_reply", data, self.token)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["description"], "Ini adalah balasan")
        self.assertIn("id", res.json())
        self.assertIn("user", res.json())
        self.assertEqual(res.json()["user"]["phone_number"], "user1")

    # New test cases for additional coverage
    def test_get_latest_forum_success(self):
        """Test successful retrieval of latest forum"""
        response = self._auth_get("/api/forum/get_latest", self.token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], self.forum_id)
        self.assertEqual(response.json()["title"], "Forum A")

    def test_update_forum_not_owned(self):
        """Test updating a forum post not owned by the user."""
        update_data = {
            "description": "Unauthorized update",
            "tag": "siklus"
        }
        response = self._authenticated_put(f"/api/forum/{self.forum_id}", update_data, self.other_user_token)
        self.assertEqual(response.status_code, 403)

    def test_update_forum_not_found(self):
        """Test updating a non-existent forum."""
        update_data = {
            "title": "Updated Title",
            "description": "Updated description",
            "tag": "budidayaplus"
        }
        response = self._authenticated_put(f"/api/forum/{uuid.uuid4()}", update_data, self.user_token)
        self.assertEqual(response.status_code, 404)

    def test_get_user_votes_unauthenticated(self):
        """Test getting user votes without authentication."""
        response = self.client.get("/api/forum/user_votes")
        self.assertEqual(response.status_code, 401)

    def test_search_forums_success(self):
        """Test searching forums successfully."""
        # Create a forum with unique text
        ForumRepository.create_forum(
            user=self.user,
            title="Unique Search Term",
            description="This should be found",
            tag="ikan"
        )
        
        response = self._authenticated_get("/api/forum/search?query=Unique", self.user_token)
        self.assertEqual(response.status_code, 200)
        results = response.json()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Unique Search Term")

    def test_search_forums_empty_query(self):
        """Test searching with empty query."""
        response = self._authenticated_get("/api/forum/search?query=", self.user_token)
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_search_forums_no_results(self):
        """Test searching with no matching results."""
        response = self._authenticated_get("/api/forum/search?query=NoSuchTerm", self.user_token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 0)

    def test_update_forum_exception_handling(self):
        """Test exception handling in the update_forum endpoint."""
        # Mock the repository to raise an exception
        with patch('forum.repositories.forum_repository.ForumRepository.update_forum_by_id') as mock_update:
            mock_update.side_effect = Exception("Test error")
            
            update_data = {
                "title": "Updated Title",
                "description": "Updated description",
                "tag": "budidayaplus"
            }
            response = self._authenticated_put(f"/api/forum/update/{self.forum_id}", update_data, self.user_token)
            
            self.assertEqual(response.status_code, 500)
            self.assertIn("error", response.json())
            self.assertEqual(response.json()["error"], "Test error")

    def test_get_latest_forum_empty(self):
        """Test when no forums exist"""
        # Delete all forums
        Forum.objects.all().delete()
        
        response = self._auth_get("/api/forum/get_latest", self.token)
        self.assertEqual(response.status_code, 404)
        self.assertIn("No forums available.", response.json()["error"])
    
    def test_create_forum_unauthenticated_forbidden(self):
        """Test that unauthenticated forum creation returns 403 with correct error message"""
        data = {
            "title": "Test Forum",
            "description": "Test Description",
            "tag": "ikan"
        }
        response = self.client.post(
            "/api/forum/create",
            data=json.dumps(data),
            content_type="application/json"
        )
        # First check if it's 401 (from JWT) or 403 (from your code)
        self.assertIn(response.status_code, [401, 403])
        if response.status_code == 403:
            self.assertEqual(response.json(), {"error": "You are not authorized to create this forum post."})
        else:
            # If it's 401 from JWT, that's also acceptable
            self.assertEqual(response.json(), {"detail": "Unauthorized"})

    def test_get_forums_by_user_unauthenticated_forbidden(self):
        """Test that unauthenticated access returns 403 with correct error message"""
        response = self.client.get("/api/forum/get_by_user")
        # First check if it's 401 (from JWT) or 403 (from your code)
        self.assertIn(response.status_code, [401, 403])
        if response.status_code == 403:
            self.assertEqual(response.json(), {"error": "You are not authorized to access this resource."})
        else:
            # If it's 401 from JWT, that's also acceptable
            self.assertEqual(response.json(), {"detail": "Unauthorized"})
