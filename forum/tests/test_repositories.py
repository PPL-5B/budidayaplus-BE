import os
from datetime import timedelta
from django.utils import timezone
from django.test import TestCase
from django.contrib.auth.models import User
from forum.models import Forum, ForumVote
from forum.repositories.forum_repository import ForumRepository
from django.http import Http404
from uuid import uuid4

class ForumRepositoryTest(TestCase):
    def setUp(self):
        self.test_password = os.getenv("TEST_USER_PASSWORD", "defaultpass123")

        self.user = User.objects.create_user(username="repo_user", password=self.test_password)
        self.other_user = User.objects.create_user(username="other_user", password=self.test_password)
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
        self.forum1.timestamp = timezone.now() - timedelta(minutes=5)
        self.forum1.save()

        self.forum2.timestamp = timezone.now()
        self.forum2.save()

        latest_forum = ForumRepository.get_latest_forum()
        self.assertEqual(latest_forum.id, self.forum2.id)

    def test_get_latest_forum_returns_none(self):
        Forum.objects.all().delete()
        self.assertIsNone(ForumRepository.get_latest_forum())

    def test_get_replies(self):
        reply = ForumRepository.create_forum(
            user=self.user,
            description="Reply to forum1",
            parent=self.forum1
        )
        replies = ForumRepository.get_replies(self.forum1)
        self.assertIn(reply, replies)

    def test_update_forum(self):
        updated = ForumRepository.update_forum(self.forum1.id, "Updated description")
        self.assertEqual(updated.description, "Updated description")

    def test_update_forum_not_found(self):
        with self.assertRaises(Http404):
            ForumRepository.update_forum(uuid4(), "Does not exist")

    def test_get_forum_by_id_not_found(self):
        with self.assertRaises(Http404):
            ForumRepository.get_forum_by_id(uuid4())

    def test_delete_forum(self):
        ForumRepository.delete_forum(self.forum1)
        with self.assertRaises(Http404):
            ForumRepository.get_forum_by_id(self.forum1.id)

    def test_get_forums_by_user_empty(self):
        new_user = User.objects.create_user(username="new_user", password=self.test_password)
        forums = ForumRepository.get_forums_by_user(new_user)
        self.assertEqual(len(forums), 0)

    def test_upvote_forum(self):
        ForumRepository.upvote_forum(self.user, self.forum1)
        vote = ForumVote.objects.get(user=self.user, forum=self.forum1)
        self.assertEqual(vote.vote_choice, 'up')

    def test_downvote_forum(self):
        ForumRepository.downvote_forum(self.user, self.forum1)
        vote = ForumVote.objects.get(user=self.user, forum=self.forum1)
        self.assertEqual(vote.vote_choice, 'down')

    def test_vote_overwritten(self):
        ForumRepository.upvote_forum(self.user, self.forum1)
        ForumRepository.downvote_forum(self.user, self.forum1)
        vote = ForumVote.objects.get(user=self.user, forum=self.forum1)
        self.assertEqual(vote.vote_choice, 'down')

    def test_cancel_vote(self):
        ForumRepository.upvote_forum(self.user, self.forum1)
        ForumRepository.cancel_vote(self.user, self.forum1)
        self.assertFalse(ForumVote.objects.filter(user=self.user, forum=self.forum1).exists())

    def test_get_vote_summary(self):
        ForumRepository.upvote_forum(self.user, self.forum1)
        ForumRepository.downvote_forum(self.other_user, self.forum1)
        summary = ForumRepository.get_vote_summary(self.forum1)
        self.assertEqual(summary['upvotes'], 1)
        self.assertEqual(summary['downvotes'], 1)
