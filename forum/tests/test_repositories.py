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
        # ubah desc
        ForumRepository.update_forum(self.f1.id, description="Baru")
        self.assertEqual(
            Forum.objects.get(id=self.f1.id).description, "Baru"
        )
        # ubah title
        ForumRepository.update_forum(self.f1.id, title="Judul Baru")
        self.assertEqual(Forum.objects.get(id=self.f1.id).title, "Judul Baru")
        # ubah tag
        ForumRepository.update_forum(self.f1.id, tag="budidayaplus")
        self.assertEqual(Forum.objects.get(id=self.f1.id).tag, "budidayaplus")
        # tidak ubah apa‑apa
        nochange = ForumRepository.update_forum(self.f1.id)
        self.assertEqual(nochange.title, "Judul Baru")
        self.assertEqual(nochange.tag, "budidayaplus")

    def test_update_not_found(self):
        with self.assertRaises(Http404):
            ForumRepository.update_forum(uuid4(), description="tak ada")

    # ---------- delete ----------
    def test_delete_forum(self):
        # Pastikan forum masih ada sebelum dihapus
        self.assertTrue(Forum.objects.filter(id=self.f1.id).exists())

        # Hapus forum
        ForumRepository.delete_forum(self.f1)

        # Pastikan forum sudah tidak ada
        self.assertFalse(Forum.objects.filter(id=self.f1.id).exists())

        # Forum lainnya tidak terhapus
        self.assertTrue(Forum.objects.filter(id=self.f2.id).exists())


    # def test_delete(self):
    #     ForumRepository.delete_forum(self.f2)
    #     with self.assertRaises(Http404):
    #         ForumRepository.get_forum_by_id(self.f2.id)

    # ---------- voting ----------
    def test_vote_cycle(self):
        ForumRepository.upvote_forum(self.user, self.f1)
        self.assertEqual(
            ForumVote.objects.get(user=self.user, forum=self.f1).vote_choice,
            "up",
        )
        ForumRepository.downvote_forum(self.user, self.f1)
        self.assertEqual(
            ForumVote.objects.get(user=self.user, forum=self.f1).vote_choice,
            "down",
        )
        ForumRepository.cancel_vote(self.user, self.f1)
        self.assertFalse(
            ForumVote.objects.filter(user=self.user, forum=self.f1).exists()
        )

    def test_vote_summary(self):
        # 2 upvotes dari user dan other
        ForumRepository.upvote_forum(self.user, self.f1)
        ForumRepository.upvote_forum(self.other, self.f1)
        summary = ForumRepository.get_vote_summary(self.f1)
        self.assertEqual(summary['upvotes'], 2)
        self.assertEqual(summary['downvotes'], 0)

        # ubah satu vote jadi down
        ForumRepository.downvote_forum(self.user, self.f1)
        summary = ForumRepository.get_vote_summary(self.f1)
        self.assertEqual(summary['upvotes'], 1)
        self.assertEqual(summary['downvotes'], 1)

        # cancel all votes
        ForumRepository.cancel_vote(self.user, self.f1)
        ForumRepository.cancel_vote(self.other, self.f1)
        summary = ForumRepository.get_vote_summary(self.f1)
        self.assertEqual(summary['upvotes'], 0)
        self.assertEqual(summary['downvotes'], 0)

