# test_api.py
from unittest.mock import patch
from django.test import TestCase, Client
from django.contrib.auth.models import User
from forum.models import Forum
import uuid
import json
from ninja_jwt.tokens import RefreshToken

class ForumAPITestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="password123")
        self.other_user = User.objects.create_user(username="otheruser", password="password123")
        self.forum = Forum.objects.create(user=self.user, description="Original Post")
        self.forum_id = str(self.forum.id)
        self.user_token = str(RefreshToken.for_user(self.user).access_token)
        self.other_user_token = str(RefreshToken.for_user(self.other_user).access_token)

    def _authenticated_post(self, url, data, token):
        """Helper method to make authenticated POST requests"""
        return self.client.post(
            url,
            data=json.dumps(data),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}"
        )

    def _authenticated_put(self, url, data, token):
        """Helper method to make authenticated PUT requests"""
        return self.client.put(
            url,
            data=json.dumps(data),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}"
        )

    def test_create_forum_success(self):
        """Test successful forum creation"""
        data = {
            "description": "My first forum post"
        }
        response = self._authenticated_post("/api/forum/create", data, self.user_token)
        self.assertEqual(response.status_code, 200)
        self.assertIn("id", response.json())
        self.assertEqual(response.json()["description"], "My first forum post")
        self.assertEqual(response.json()["user"], self.user.id)


    def test_create_forum_with_parent(self):
        parent_data = {
            "description": "Parent forum post"
        }
        parent_response = self._authenticated_post("/api/forum/create", parent_data, self.user_token)
        parent_id = parent_response.json()["id"]

        reply_data = {
            "description": "Reply to parent post",
            "parent_id": parent_id
        }
        reply_response = self._authenticated_post("/api/forum/create", reply_data, self.user_token)
       
        self.assertEqual(reply_response.status_code, 200)
        self.assertEqual(reply_response.json()["description"], "Reply to parent post")
        self.assertEqual(reply_response.json()["parent"], parent_id)


    def test_create_forum_unauthenticated(self):
        data = {
            "description": "Unauthenticated post"
        }
        response = self.client.post(
            "/api/forum/create",
            data=json.dumps(data),
            content_type="application/json"
        )
       
        self.assertEqual(response.status_code, 403)
        self.assertIn("error", response.json())


    def test_create_forum_invalid_parent(self):
        invalid_parent_data = {
            "description": "Child forum with invalid parent",
            "parent_id": str(uuid.uuid4())  
        }
        response = self._authenticated_post("/api/forum/create", invalid_parent_data, self.user_token)
       
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_update_forum_success(self):
        """Test update forum by its owner"""
        forum = Forum.objects.create(user=self.user, description="Original Post")

        update_data = {"description": "Updated description"}
        response = self._authenticated_put(
            f"/api/forum/{forum.id}/",
            update_data,
            self.user_token
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["description"], "Updated description")


    def test_update_forum_unauthorized(self):
        forum = Forum.objects.create(user=self.user, description="Original Post")

        update_data = {"description": "Hacked description"}
        response = self._authenticated_put(
            f"/api/forum/{forum.id}/",
            update_data,
            self.other_user_token
        )

        self.assertEqual(response.status_code, 403)
        self.assertIn("error", response.json())

    def test_update_forum_not_found(self):
        fake_forum_id = str(uuid.uuid4())
        update_data = {"description": "Some description"}
        response = self._authenticated_put(
            f"/api/forum/{fake_forum_id}/",
            update_data,
            self.user_token
        )
        self.assertEqual(response.status_code, 404)

    def test_update_forum_unauthenticated(self):
        """Test update forum without authentication"""
        forum = Forum.objects.create(user=self.user, description="Original Post")

        update_data = {"description": "Unauthenticated update"}
        response = self.client.put(
            f"/api/forum/{forum.id}/",
            data=json.dumps(update_data),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("error", response.json())

    def test_create_forum_empty_description(self):
        data = {
            "description": ""
        }
        response = self._authenticated_post("/api/forum/create", data, self.user_token)
        self.assertIn(response.status_code, [200, 400])

    def test_update_forum_empty_description(self):
        forum = Forum.objects.create(user=self.user, description="Original Post")

        update_data = {"description": ""}
        response = self._authenticated_put(
            f"/api/forum/{forum.id}/",
            update_data,
            self.user_token
        )
        self.assertIn(response.status_code, [200, 400])
   
    def test_create_forum_with_disabled_user(self):
        disabled_user = User.objects.create_user(username="disableduser", password="password123")
        disabled_user.is_active = False
        disabled_user.save()
        disabled_user_token = str(RefreshToken.for_user(disabled_user).access_token)
        data = {
            "description": "Attempt to create forum with disabled account"
        }
       
        response = self.client.post(
            "/api/forum/create",
            data=json.dumps(data),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {disabled_user_token}"
        )
       
        self.assertEqual(response.status_code, 403)
        self.assertIn("error", response.json())
        self.assertEqual(
            response.json()["error"],
            "You are not authorized to create this forum post."
        )

    def test_create_forum_with_insufficient_permissions(self):
        restricted_user = User.objects.create_user(username="restricteduser", password="password123")
        restricted_user_token = str(RefreshToken.for_user(restricted_user).access_token)

        data = {
            "description": "Attempt to create forum with restricted account"
        }
       
        response = self.client.post(
            "/api/forum/create",
            data=json.dumps(data),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {restricted_user_token}"
        )
       
        self.assertEqual(response.status_code, 403)
        self.assertIn("error", response.json())

    def test_create_forum_with_parent_from_different_user(self):
        parent_forum = Forum.objects.create(
            user=self.other_user,
            description="Parent forum by another user"
        )

        reply_data = {
            "description": "Reply to another user's forum",
            "parent_id": str(parent_forum.id)
        }
       
        response = self._authenticated_post("/api/forum/create", reply_data, self.user_token)
 
        self.assertEqual(response.status_code, 200)  # or 403 if replies are restricted
        if response.status_code == 200:
            self.assertEqual(response.json()["parent"], str(parent_forum.id))


    def test_create_forum_with_malformed_parent_id(self):
        malformed_parent_ids = [
            "not-a-valid-uuid",
            "123456",
            "00000000-0000-0000-0000-000000000000",  # null UUID
            None
        ]
       
        for bad_parent_id in malformed_parent_ids:
            data = {
                "description": "Forum with malformed parent ID",
                "parent_id": bad_parent_id
            }
           
            response = self._authenticated_post("/api/forum/create", data, self.user_token)
           
            self.assertEqual(response.status_code, 400)
            self.assertIn("error", response.json())


    def test_create_forum_multiple_consecutive_requests(self):
        forum_descriptions = [
            "First consecutive forum post",
            "Second consecutive forum post",
            "Third consecutive forum post"
        ]
       
        responses = []
        for description in forum_descriptions:
            data = {"description": description}
            response = self._authenticated_post("/api/forum/create", data, self.user_token)
            responses.append(response)
       
        for response in responses:
            self.assertEqual(response.status_code, 200)
            self.assertIn("id", response.json())
            self.assertIn("description", response.json())

    def test_create_forum_with_long_description(self):
        long_description = "x" * 10000  
       
        data = {
            "description": long_description
        }
       
        response = self._authenticated_post("/api/forum/create", data, self.user_token)
        self.assertIn(response.status_code, [200, 400])
        if response.status_code == 400:
            self.assertIn("error", response.json())

    def test_authenticated_user_can_create_post(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")
        data = {"description": "This is a test forum post."}
        response = self.client.post(self.url, data, content_type="application/json")
        self.assertNotEqual(response.status_code, 403)

    def test_unauthenticated_user_cannot_create_post(self):
        data = {"description": "This is a test forum post."}
        response = self.client.post(self.url, data, content_type="application/json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json(), {"error": "You are not authorized to create this forum post."})

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