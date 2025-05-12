import os
from datetime import timedelta
from uuid import uuid4
from django.utils import timezone
from django.test import TestCase
from django.contrib.auth.models import User
from django.http import Http404
from django.db.models import Q

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
        # Create a forum with a different user
        self.f3 = ForumRepository.create_forum(
            user=self.other, title="P3", description="Z", tag="ikan"
        )

    # ---------- basic CRUD operations ----------
    def test_get_forum_by_id(self):
        self.assertEqual(ForumRepository.get_forum_by_id(self.f1.id), self.f1)
        with self.assertRaises(Http404):
            ForumRepository.get_forum_by_id(uuid4())

    def test_list_forums(self):
        # Test default listing
        forums = ForumRepository.list_forums()
        self.assertEqual(len(forums), 3)
        
        # Test pagination
        limited = ForumRepository.list_forums(limit=2)
        self.assertEqual(len(limited), 2)
        
        offset = ForumRepository.list_forums(limit=1, offset=1)
        self.assertEqual(len(offset), 1)

    def test_get_forums_by_user(self):
        user_forums = ForumRepository.get_forums_by_user(self.user)
        self.assertEqual(len(user_forums), 2)
        self.assertTrue(all(f.user == self.user for f in user_forums))

    def test_create_forum(self):
        # Test creating a new forum
        new_forum = ForumRepository.create_forum(
            user=self.user,
            title="New Forum",
            description="New Description",
            tag="budidayaplus"
        )
        self.assertEqual(new_forum.title, "New Forum")
        self.assertEqual(new_forum.tag, "budidayaplus")
        
        # Test creating a reply with auto-generated title
        reply = ForumRepository.create_forum(
            user=self.user,
            title=None,
            description="Reply content",
            parent=self.f1,
            tag="siklus"
        )
        self.assertIn("Reply", reply.title)
        self.assertEqual(reply.parent, self.f1)

    def test_latest_forum(self):
        self.f1.timestamp = timezone.now() - timedelta(minutes=10)
        self.f1.save()
        self.f2.timestamp = timezone.now()
        self.f2.save()
        self.assertEqual(
            ForumRepository.get_latest_forum().id,
            self.f2.id,
        )

    def test_latest_forum_none(self):
        Forum.objects.all().delete()
        self.assertIsNone(ForumRepository.get_latest_forum())

    # ---------- tag filtering ----------
    def test_get_forums_by_tag(self):
        ikan_forums = ForumRepository.get_forums_by_tag("ikan")
        self.assertEqual(len(ikan_forums), 2)
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
    def test_get_replies(self):
        reply = ForumRepository.create_forum(
            user=self.user,
            title="Reply",
            description="Reply content",
            parent=self.f1,
            tag="siklus"
        )

        replies = ForumRepository.get_replies(self.f1)
        self.assertEqual(len(replies), 1)
        self.assertEqual(replies[0], reply)

    def test_get_replies_empty(self):
        replies = ForumRepository.get_replies(self.f2)
        self.assertEqual(len(replies), 0)

    # ---------- update operations ----------
    def test_update_forum(self):
        # Update title and description
        updated = ForumRepository.update_forum_by_id(
            self.f1.id,
            title="Updated Title",
            description="Updated Description"
        )
        self.assertEqual(updated.title, "Updated Title")
        self.assertEqual(updated.description, "Updated Description")
        
        # Verify changes persisted
        refreshed = Forum.objects.get(id=self.f1.id)
        self.assertEqual(refreshed.title, "Updated Title")

    def test_update_forum_not_found(self):
        with self.assertRaises(Http404):
            ForumRepository.update_forum_by_id(uuid4(), title="Not exist", description="Not exist")

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

    # ---------- voting operations ----------
    def test_vote_operations(self):
        # Test upvote
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

    # ---------- search operations ----------
    def test_search_forums(self):
        # Create a forum with unique text
        unique_forum = ForumRepository.create_forum(
            user=self.user,
            title="Unique Search Term",
            description="This should be found",
            tag="ikan"
        )
        
        # Search by title
        results = ForumRepository.search_forums("Unique")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].id, unique_forum.id)
        
        # Search by description
        results = ForumRepository.search_forums("should be found")
        self.assertEqual(len(results), 1)
        
        # Search with no results
        results = ForumRepository.search_forums("nonexistent term")
        self.assertEqual(len(results), 0)

    def test_search_forums_excludes_replies(self):
        # Create a reply
        ForumRepository.create_forum(
            user=self.user,
            title="Reply with search term",
            description="This is a reply",
            parent=self.f1,
            tag="ikan"
        )
        
        # Search shouldn't return replies
        results = ForumRepository.search_forums("reply")
        self.assertEqual(len(results), 0)

    # ---------- edge cases ----------
    def test_create_forum_empty_title(self):
        # Main post requires title
        with self.assertRaises(Exception):
            ForumRepository.create_forum(
                user=self.user,
                description="Content",
                tag="ikan"
            )
        
        # Reply can have empty title (will be auto-generated)
        reply = ForumRepository.create_forum(
            user=self.user,
            title=None,
            description="Reply content",
            parent=self.f1,
            tag="ikan"
        )
        self.assertTrue(reply.title.startswith("Reply"))

    def test_update_forum_partial(self):
        # Update only description
        updated = ForumRepository.update_forum_by_id(
            self.f1.id,
            title=self.f1.title,
            description="Only update description"
        )
        self.assertEqual(updated.title, self.f1.title)  # unchanged
        self.assertEqual(updated.description, "Only update description")
