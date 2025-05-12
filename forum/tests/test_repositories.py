import os
from datetime import timedelta
from uuid import uuid4
from django.utils import timezone
from django.test import TestCase
from django.contrib.auth.models import User
from django.http import Http404

from forum.models import Forum, ForumVote
from forum.repositories.forum_repository import ForumRepository


class ForumRepositoryTest(TestCase):
    def setUp(self):
        pwd = os.getenv("TEST_USER_PASSWORD", "defaultpass123")
        self.user = User.objects.create_user("repo", password=pwd)
        self.other = User.objects.create_user("repo2", password=pwd)

        self.f1 = ForumRepository.create_forum(
            user=self.user, title="P1", description="X", tag="ikan"
        )
        self.f2 = ForumRepository.create_forum(
            user=self.user, title="P2", description="Y", tag="kolam"
        )

    # ---------- basic ----------
    def test_get_methods(self):
        self.assertEqual(ForumRepository.get_forum_by_id(self.f1.id), self.f1)
        self.assertEqual(len(ForumRepository.list_forums()), 2)
        self.assertEqual(len(ForumRepository.get_forums_by_user(self.user)), 2)
        self.assertEqual(self.f1.tag, "ikan")
        self.assertEqual(self.f2.tag, "kolam")

    def test_latest(self):
        self.f1.timestamp = timezone.now() - timedelta(minutes=10)
        self.f1.save()
        self.f2.timestamp = timezone.now()
        self.f2.save()
        self.assertEqual(
            ForumRepository.get_latest_forum().id,
            self.f2.id,
        )

    def test_latest_none(self):
        Forum.objects.all().delete()
        self.assertIsNone(ForumRepository.get_latest_forum())

    def test_get_forums_by_tag(self):
        ikan_forums = ForumRepository.get_forums_by_tag("ikan")
        self.assertEqual(len(ikan_forums), 1)
        self.assertEqual(ikan_forums[0].tag, "ikan")

        kolam_forums = ForumRepository.get_forums_by_tag("kolam")
        self.assertEqual(len(kolam_forums), 1)
        self.assertEqual(kolam_forums[0].tag, "kolam")

    def test_get_forums_by_tag_empty(self):
        forums = ForumRepository.get_forums_by_tag("budidayaplus")
        self.assertEqual(len(forums), 0)

    def test_get_forums_by_tag_invalid(self):
        forums = ForumRepository.get_forums_by_tag("invalid_tag")
        self.assertEqual(len(forums), 0)

    # ---------- replies ----------
    def test_replies_and_auto_title(self):
        reply = ForumRepository.create_forum(
            user=self.user,
            title=None,
            description="Balas",
            parent=self.f1,
            tag="siklus"
        )
        self.assertIn(reply, ForumRepository.get_replies(self.f1))
        self.assertTrue(reply.title.startswith("Reply"))
        self.assertEqual(reply.tag, "siklus")

    # ---------- update ----------
    def test_update_paths(self):
        ForumRepository.update_forum(self.f1.id, title=None, description="Baru")
        self.assertEqual(Forum.objects.get(id=self.f1.id).description, "Baru")

        ForumRepository.update_forum(self.f1.id, title="Judul Baru", description=None)
        self.assertEqual(Forum.objects.get(id=self.f1.id).title, "Judul Baru")

        ForumRepository.update_forum(self.f1.id, title=None, description=None)
        updated = Forum.objects.get(id=self.f1.id)
        self.assertEqual(updated.title, "Judul Baru")
        self.assertEqual(updated.description, "Baru")

    def test_update_not_found(self):
        with self.assertRaises(Http404):
            ForumRepository.update_forum(uuid4(), title=None, description="tak ada")

    # ---------- delete ----------
    def test_delete(self):
        ForumRepository.delete_forum(self.f2)
        with self.assertRaises(Http404):
            ForumRepository.get_forum_by_id(self.f2.id)

    # ---------- voting ----------
    def test_vote_cycle(self):
        ForumRepository.upvote_forum(self.user, self.f1)
        self.assertTrue(
            ForumVote.objects.filter(user=self.user, forum=self.f1).exists()
        )

        ForumRepository.cancel_vote(self.user, self.f1)
        self.assertFalse(
            ForumVote.objects.filter(user=self.user, forum=self.f1).exists()
        )

    def test_vote_summary(self):
        ForumRepository.upvote_forum(self.user, self.f1)
        ForumRepository.upvote_forum(self.other, self.f1)

        summary = ForumRepository.get_vote_summary(self.f1)
        self.assertEqual(summary['upvotes'], 2)

        ForumRepository.cancel_vote(self.user, self.f1)
        summary = ForumRepository.get_vote_summary(self.f1)
        self.assertEqual(summary['upvotes'], 1)

        ForumRepository.cancel_vote(self.other, self.f1)
        summary = ForumRepository.get_vote_summary(self.f1)
        self.assertEqual(summary['upvotes'], 0)
