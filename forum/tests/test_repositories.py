from uuid import uuid4
from django.test import TestCase
from django.contrib.auth.models import User
from forum.models import Forum
from forum.repositories.forum_repository import ForumRepository
from django.http import Http404

class ForumRepositoryTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='repo_user', password='testpass')
        self.forum1 = ForumRepository.create_forum(
            user=self.user,
            description="Forum post 1"
        )
        self.forum2 = ForumRepository.create_forum(
            user=self.user,
            description="Forum post 2"
        )

    def test_get_forum_by_id(self):
        forum = ForumRepository.get_forum_by_id(self.forum1.id)
        self.assertEqual(forum, self.forum1)

    def test_list_forums(self):
        forums = ForumRepository.list_forums()
        self.assertEqual(len(forums), 2)

    def test_get_forums_by_user(self):
        forums = ForumRepository.get_forums_by_user(self.user)
        self.assertEqual(len(forums), 2)

    def test_get_latest_forum(self):
        latest_forum = ForumRepository.get_latest_forum()
        manually_latest = Forum.objects.order_by('-timestamp').first()
        self.assertEqual(latest_forum.id, manually_latest.id)

    def test_delete_forum(self):
        ForumRepository.delete_forum(self.forum1)
        forums = ForumRepository.list_forums()
        self.assertEqual(len(forums), 1)
        with self.assertRaises(Http404):
            ForumRepository.get_forum_by_id(self.forum1.id)
            
    def test_get_latest_forum_returns_none_when_no_forum(self):
        Forum.objects.all().delete()
        
        latest_forum = ForumRepository.get_latest_forum()
        self.assertIsNone(latest_forum)

    def test_update_forum(self):
        updated_forum = ForumRepository.update_forum(
            forum_id=self.forum1.id,
            description="Updated Forum post"
        )
        self.assertEqual(updated_forum.description, "Updated Forum post")

        forum_from_db = Forum.objects.get(id=self.forum1.id)
        self.assertEqual(forum_from_db.description, "Updated Forum post")

    def test_get_forum_by_id_not_found(self):
        non_existent_id = uuid4()
        with self.assertRaises(Http404):
            ForumRepository.get_forum_by_id(non_existent_id)

    def test_get_forums_by_user_empty(self):
        # Test with user that has no forums
        new_user = User.objects.create_user(username='new_user', password='testpass')
        forums = ForumRepository.get_forums_by_user(new_user)
        self.assertEqual(len(forums), 0)

    def test_update_forum_not_found(self):
        non_existent_id = uuid4()
        with self.assertRaises(Http404):
            ForumRepository.update_forum(
                forum_id=non_existent_id,
                description="Should fail"
            )