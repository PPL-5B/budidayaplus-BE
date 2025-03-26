from django.test import TestCase
from django.contrib.auth.models import User
from forum.models import Forum

class ForumModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser")
        self.user.set_password("testpass") 
        self.user.save()

    def test_create_forum_model(self):
        forum = Forum.objects.create(
            user=self.user,
            description="Test forum description"
        )
        self.assertIsNotNone(forum.id)
        self.assertEqual(forum.user, self.user)
        self.assertEqual(forum.description, "Test forum description")
        self.assertIsNotNone(forum.timestamp)
        self.assertIn(self.user.username, str(forum))