# test_api.py
from django.test import TestCase, Client
from django.contrib.auth.models import User
from forum.models import Forum
import uuid
import json

class ForumUpdateTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="password123")
        self.other_user = User.objects.create_user(username="otheruser", password="password123")
        self.forum = Forum.objects.create(user=self.user, description="Original Post")

    def test_update_forum_success(self):
        """Test update forum oleh pemiliknya"""
        self.client.login(username="testuser", password="password123")

        update_data = {"description": "Updated description"}
        response = self.client.put(
            f"/api/forum/{self.forum.id}/", 
            data=json.dumps(update_data), 
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 200)

        self.forum.refresh_from_db()
        self.assertEqual(self.forum.description, "Updated description")

    def test_update_forum_unauthorized(self):
        """Test update forum oleh user yang bukan pemilik (harus gagal dengan 403)"""
        self.client.login(username="otheruser", password="password123")

        update_data = {"description": "Hacked description"}
        response = self.client.put(
            f"/api/forum/{self.forum.id}/", 
            data=json.dumps(update_data), 
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 403)
        self.assertIn("error", response.json())

        self.forum.refresh_from_db()
        self.assertNotEqual(self.forum.description, "Hacked description")

    def test_update_forum_not_found(self):
        """Test update forum yang tidak ada (harus gagal dengan 404)"""
        self.client.login(username="testuser", password="password123")

        fake_forum_id = str(uuid.uuid4())  # UUID random yang tidak ada di database
        update_data = {"description": "Some description"}
        response = self.client.put(
            f"/api/forum/{fake_forum_id}/", 
            data=json.dumps(update_data), 
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 404)

    def test_update_forum_unauthenticated(self):
        """Test update forum tanpa login (harus gagal dengan 403)"""
        update_data = {"description": "Unauthenticated update"}
        response = self.client.put(
            f"/api/forum/{self.forum.id}/", 
            data=json.dumps(update_data), 
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 403)
        self.assertIn("error", response.json())

        self.forum.refresh_from_db()
        self.assertNotEqual(self.forum.description, "Unauthenticated update")