import os
from unittest.mock import patch
from django.test import TestCase, Client
from django.contrib.auth.models import User
import uuid

import json
import uuid
from datetime import timedelta
from types import SimpleNamespace

from django.test import TestCase, Client
from django.utils import timezone
from django.contrib.auth.models import User, AnonymousUser
from ninja_jwt.tokens import RefreshToken
from ninja.responses import Response
from forum.models import Forum, ForumVote
from forum.repositories.forum_repository import ForumRepository
from forum.api import create_forum, get_forums_by_user, get_forum_by_id
from forum.schemas import ForumCreateSchema
from types import SimpleNamespace
from forum.api import create_forum, get_forums_by_user
from forum.schemas import ForumCreateSchema
from types import SimpleNamespace
from forum.api import get_replies
from forum.models import Forum

class ForumAPITestCase(TestCase):
    def _token(self, user: User):
        return str(RefreshToken.for_user(user).access_token)

    def _req(self, method: str, url: str, token=None, body=None):
        hdrs = {"content_type": "application/json"}
        if token:
            hdrs["HTTP_AUTHORIZATION"] = f"Bearer {token}"
        if body is not None:
            hdrs["data"] = json.dumps(body)

        match method:
            case "GET":
                return self.client.get(url, **hdrs)
            case "POST":
                return self.client.post(url, **hdrs)
            case "PUT":
                return self.client.put(url, **hdrs)
            case "DELETE":
                return self.client.delete(url, **hdrs)
        raise ValueError("Bad HTTP verb")

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="password123")
        self.other_user = User.objects.create_user(username="otheruser", password="password123")
        self.forum = ForumRepository.create_forum(
            user=self.user, 
            title="Test Forum", 
            description="Original Post",
            tag="ikan"
        )
        self.forum_id = str(self.forum.id)
        self.user_token = str(RefreshToken.for_user(self.user).access_token)
        self.other_user_token = str(RefreshToken.for_user(self.other_user).access_token)

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

    def test_manual_unauthorized_branches(self):
        fake_request = SimpleNamespace(user=AnonymousUser())

        # create_forum -> 403
        data = ForumCreateSchema(title="X", description="Y")
        resp: Response = create_forum(fake_request, data)
        self.assertEqual(resp.status_code, 403)

        # get_forums_by_user -> 403
        resp2: Response = get_forums_by_user(fake_request)
        self.assertEqual(resp2.status_code, 403)

    def test_create_and_reply(self):
        ok = self._req(
            "POST",
            "/api/forum/create_reply",
            token=self.user_token,
            body={
                "description": "Ini reply",
                "parent_id": self.forum_id,
                "tag": "ikan"
            }
        )
        self.assertEqual(ok.status_code, 200)

    def test_create_forum_success(self):
        """Test creating a forum post successfully."""
        data = {
            "title": "Test Forum",
            "description": "My first forum post",
            "tag": "ikan"
        }
        response = self._authenticated_post("/api/forum/create", data, self.user_token)
        self.assertEqual(response.status_code, 200)
        resp_json = response.json()
        self.assertIn("id", resp_json)
        self.assertIn("user", resp_json)
        self.assertEqual(resp_json["description"], "My first forum post")
        self.assertEqual(resp_json["tag"], "ikan")
        self.assertIsNone(resp_json.get("parent_id"))

    def test_create_forum_unauthenticated(self):
        """Test that creating a forum post without a token returns 401."""
        data = {
            "title": "Test Forum",
            "description": "No token here",
            "tag": "ikan"
        }
        response = self.client.post(
            "/api/forum/create",
            data=json.dumps(data),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 401)

    def test_create_forum_invalid_parent(self):
        """Test creating a forum with invalid parent ID."""
        data = {
            "title": "Test Forum",
            "description": "Post with non-existent parent",
            "parent_id": str(uuid.uuid4()),
            "tag": "ikan"
        }
        response = self._authenticated_post("/api/forum/create", data, self.user_token)
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_create_reply_success(self):
        """Test creating a reply to an existing forum post."""
        parent_data = {
            "title": "Parent Forum",
            "description": "Parent forum post",
            "tag": "ikan"
        }
        parent_response = self._authenticated_post("/api/forum/create", parent_data, self.user_token)
        self.assertEqual(parent_response.status_code, 200)
        parent_id = parent_response.json()["id"]

        reply_data = {
            "description": "This is a reply",
            "parent_id": parent_id,
            "tag": "kolam"
        }
        reply_response = self._authenticated_post("/api/forum/create_reply", reply_data, self.user_token)
        self.assertEqual(reply_response.status_code, 200)
        reply_json = reply_response.json()
        self.assertIn("id", reply_json)
        self.assertIn("user", reply_json)
        self.assertEqual(reply_json["description"], "This is a reply")
        self.assertEqual(reply_json["tag"], "kolam")

    def test_create_reply_no_parent_id(self):
        """Test creating a reply without providing a parent_id."""
        reply_data = {
            "description": "This is a reply",
            "tag": "kolam"
        }
        response = self._authenticated_post("/api/forum/create_reply", reply_data, self.user_token)
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_create_reply_invalid_parent(self):
        """Test creating a reply with an invalid parent ID."""
        reply_data = {
            "description": "This is a reply",
            "parent_id": str(uuid.uuid4()),
            "tag": "kolam"
        }
        response = self._authenticated_post("/api/forum/create_reply", reply_data, self.user_token)
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_delete_forum_success(self):
        """Test deleting a forum post successfully."""
        forum = ForumRepository.create_forum(
            user=self.user,
            title="Forum to delete",
            description="Delete me",
            tag="ikan"
        )
        response = self._authenticated_delete(f"/api/forum/delete/{forum.id}", self.user_token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "Forum deleted successfully.")

    def test_delete_forum_not_found(self):
        """Test deleting a non-existent forum."""
        response = self._authenticated_delete(f"/api/forum/delete/{uuid.uuid4()}", self.user_token)
        self.assertEqual(response.status_code, 404)
        self.assertIn("error", response.json())

    def test_delete_forum_not_owned(self):
        """Test deleting a forum post not owned by the user."""
        response = self._authenticated_delete(f"/api/forum/delete/{self.forum_id}", self.other_user_token)
        self.assertEqual(response.status_code, 403)
        self.assertIn("error", response.json())

    def test_delete_forum_unauthenticated(self):
        """Test deleting a forum post without authentication."""
        response = self.client.delete(f"/api/forum/delete/{self.forum_id}")
        self.assertEqual(response.status_code, 401)

    def test_get_forum_by_id_success(self):
        """Test retrieving a forum by its ID."""
        response = self._authenticated_get(f"/api/forum/get_by_id/{self.forum_id}", self.user_token)
        self.assertEqual(response.status_code, 200)
        resp_json = response.json()
        self.assertEqual(resp_json["id"], str(self.forum_id))
        self.assertEqual(resp_json["tag"], "ikan")

    def test_get_forum_by_id_not_found(self):
        """Test retrieving a non-existent forum by ID."""
        response = self._authenticated_get(f"/api/forum/get_by_id/{uuid.uuid4()}", self.user_token)
        self.assertEqual(response.status_code, 404)
        self.assertIn("error", response.json())

    def test_list_forums_success(self):
        """Test retrieving a list of all forums."""
        # Create another forum with different tag
        ForumRepository.create_forum(
            user=self.user,
            title="Another Forum",
            description="Another post",
            tag="kolam"
        )
        response = self._authenticated_get("/api/forum/list", self.user_token)
        self.assertEqual(response.status_code, 200)
        forums = response.json()
        self.assertEqual(len(forums), 2)
        self.assertEqual(forums[0]["tag"], "ikan")
        self.assertEqual(forums[1]["tag"], "kolam")

    def test_list_forums_pagination(self):
        """Test pagination in list forums endpoint."""
        # Create multiple forums
        for i in range(15):
            ForumRepository.create_forum(
                user=self.user,
                title=f"Forum {i}",
                description=f"Description {i}",
                tag="ikan"
            )
        
        # Test limit
        response = self._authenticated_get("/api/forum/list?limit=5", self.user_token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 5)
        
        # Test offset
        response = self._authenticated_get("/api/forum/list?limit=5&offset=5", self.user_token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 5)
        self.assertEqual(response.json()[0]["title"], "Forum 5")

    def test_get_forums_by_user_success(self):
        """Test retrieving forums created by the authenticated user."""
        response = self._authenticated_get("/api/forum/get_by_user", self.user_token)
        self.assertEqual(response.status_code, 200)
        forums = response.json()
        self.assertEqual(len(forums), 1)
        self.assertEqual(forums[0]["tag"], "ikan")

    def test_get_forums_by_user_unauthenticated(self):
        """Test retrieving forums by user without authentication."""
        response = self.client.get("/api/forum/get_by_user")
        self.assertEqual(response.status_code, 401)

    def test_get_latest_forum_success(self):
        """Test retrieving the latest forum."""
        # Create a newer forum
        new_forum = ForumRepository.create_forum(
            user=self.user,
            title="Newer Forum",
            description="Latest post",
            tag="siklus"
        )
        new_forum.timestamp = timezone.now()
        new_forum.save()

        response = self._authenticated_get("/api/forum/get_latest", self.user_token)
        self.assertEqual(response.status_code, 200)
        resp_json = response.json()
        self.assertEqual(resp_json["tag"], "siklus")

    def test_get_latest_forum_not_found(self):
        """Test retrieving the latest forum when no forums exist."""
        # Delete all forums to ensure no forum exists
        Forum.objects.all().delete()
        response = self._authenticated_get("/api/forum/get_latest", self.user_token)
        self.assertEqual(response.status_code, 404)
        self.assertIn("error", response.json())
        self.assertEqual(response.json()["error"], "No forums available.")

    def test_get_forums_by_tag_api_success(self):
        """Test the API endpoint for getting forums by tag."""
        # Create another forum with 'ikan' tag for testing multiple results
        ForumRepository.create_forum(
            user=self.other_user,
            title="Another Ikan Forum",
            description="Another post about fish",
            tag="ikan"
        )
        
        response = self._authenticated_get("/api/forum/get_by_tag/ikan", self.user_token)
        self.assertEqual(response.status_code, 200)
        forums = response.json()
        self.assertEqual(len(forums), 2)
        self.assertTrue(all(forum["tag"] == "ikan" for forum in forums))

    def test_get_forums_by_tag_api_no_results(self):
        """Test the API endpoint for getting forums by tag when none exist."""
        response = self._authenticated_get("/api/forum/get_by_tag/budidayaplus", self.user_token)
        self.assertEqual(response.status_code, 200)
        forums = response.json()
        self.assertEqual(len(forums), 0)
        
    def test_get_forums_by_tag_api_invalid_tag(self):
        """Test the API endpoint with an invalid tag."""
        response = self._authenticated_get("/api/forum/get_by_tag/invalid_tag", self.user_token)
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())
        self.assertTrue("Invalid tag" in response.json()["error"])

    def test_get_forums_by_tag_api_unauthenticated(self):
        """Test the API endpoint without authentication."""
        response = self.client.get("/api/forum/get_by_tag/ikan")
        self.assertEqual(response.status_code, 401)

    def test_get_replies_success(self):
        """Test retrieving replies for a forum."""
        ForumRepository.create_forum(
            user=self.user,
            title="Reply Title",
            description="Reply content",
            parent=self.forum,
            tag="kolam"
        )
        response = self._authenticated_get(f"/api/forum/get_replies/{self.forum_id}", self.user_token)
        self.assertEqual(response.status_code, 200)
        replies = response.json()
        self.assertEqual(len(replies), 1)
        self.assertEqual(replies[0]["tag"], "kolam")
        self.assertEqual(replies[0]["title"], "Reply Title")

    def test_get_replies_forum_not_found(self):
        """Test retrieving replies for a non-existent forum."""
        response = self._authenticated_get(f"/api/forum/get_replies/{uuid.uuid4()}", self.user_token)
        self.assertEqual(response.status_code, 404)
        self.assertIn("error", response.json())

    def test_update_forum_success(self):
        """Test updating a forum post successfully."""
        update_data = {
            "title": "Updated Title",
            "description": "Updated description",
            "tag": "budidayaplus"
        }
        response = self._authenticated_put(f"/api/forum/{self.forum_id}", update_data, self.user_token)
        self.assertEqual(response.status_code, 200)
        resp_json = response.json()
        self.assertEqual(resp_json["title"], "Updated Title")
        self.assertEqual(resp_json["description"], "Updated description")
        self.assertEqual(resp_json["tag"], "budidayaplus")

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

    def test_vote_operations(self):
        """Test upvote, downvote, and cancel vote operations."""
        # Test upvote
        response = self._authenticated_post(f"/api/forum/upvote/{self.forum_id}", {}, self.user_token)
        self.assertEqual(response.status_code, 204)
        
        # Test vote summary after upvote
        response = self._authenticated_get(f"/api/forum/vote_summary/{self.forum_id}", self.user_token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["upvotes"], 1)
        self.assertEqual(response.json()["user_vote"], "upvote")
        
        # Test downvote (should replace upvote)
        response = self._authenticated_post(f"/api/forum/downvote/{self.forum_id}", {}, self.user_token)
        self.assertEqual(response.status_code, 204)
        
        # Test vote summary after downvote
        response = self._authenticated_get(f"/api/forum/vote_summary/{self.forum_id}", self.user_token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["downvotes"], 1)
        self.assertEqual(response.json()["user_vote"], "downvote")
        
        # Test cancel vote
        response = self._authenticated_delete(f"/api/forum/cancel_vote/{self.forum_id}", self.user_token)
        self.assertEqual(response.status_code, 204)
        
        # Test vote summary after cancel
        response = self._authenticated_get(f"/api/forum/vote_summary/{self.forum_id}", self.user_token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["upvotes"], 0)
        self.assertEqual(response.json()["downvotes"], 0)
        self.assertIsNone(response.json()["user_vote"])

    def test_get_user_votes(self):
        """Test getting all votes by a user."""
        # First create some votes
        forum2 = ForumRepository.create_forum(
            user=self.user,
            title="Forum 2",
            description="Another post",
            tag="kolam"
        )
        
        # Upvote first forum
        self._authenticated_post(f"/api/forum/upvote/{self.forum_id}", {}, self.user_token)
        # Downvote second forum
        self._authenticated_post(f"/api/forum/downvote/{forum2.id}", {}, self.user_token)
        
        # Get user votes
        response = self._authenticated_get("/api/forum/user_votes", self.user_token)
        self.assertEqual(response.status_code, 200)
        votes = response.json()["votes"]
        self.assertEqual(len(votes), 2)
        
        # Check the votes are correct
        vote_forums = {v["forum__id"]: v["vote_choice"] for v in votes}
        self.assertEqual(vote_forums[str(self.forum_id)], "upvote")
        self.assertEqual(vote_forums[str(forum2.id)], "downvote")

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

    def test_direct_unauthorized_branches(self):
        """
        Panggil handler secara langsung dengan AnonymousUser agar baris
        'return Response(..., 403)' ter-eksekusi (create & get_by_user).
        """
        fake_request = SimpleNamespace(user=AnonymousUser())

        # ---- create_forum (parent None, title ada) → expected 403 ----
        payload = ForumCreateSchema(
            title="Judul",
            description="Desc",
            tag="ikan",
        )
        resp = create_forum(fake_request, payload)
        self.assertEqual(resp.status_code, 403)

        # ---- get_forums_by_user → expected 403 ----
        resp2 = get_forums_by_user(fake_request)
        self.assertEqual(resp2.status_code, 403)

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

    def test_vote_summary_no_vote(self):
        """Test vote summary when user hasn't voted."""
        response = self._authenticated_get(f"/api/forum/vote_summary/{self.forum_id}", self.user_token)
        self.assertEqual(response.status_code, 200)
        summary = response.json()
        self.assertEqual(summary["upvotes"], 0)
        self.assertEqual(summary["downvotes"], 0)
        self.assertIsNone(summary["user_vote"])