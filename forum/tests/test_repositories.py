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
        self.assertEqual(latest_forum, self.forum2)

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

    def test_get_replies(self):
        # Initially, forum1 should have no replies.
        replies = ForumRepository.get_replies(self.forum1)
        self.assertEqual(len(replies), 0)
        reply = ForumRepository.create_forum(
            user=self.user,
            description="Reply to forum1",
            parent=self.forum1
        )
        replies = ForumRepository.get_replies(self.forum1)
        self.assertEqual(len(replies), 1)
        self.assertEqual(replies[0], reply)
