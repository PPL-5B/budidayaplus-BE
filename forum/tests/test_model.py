import os
from django.test import TestCase
from django.contrib.auth.models import User
from forum.models import Forum, ForumVote
from django.db.utils import IntegrityError

class ForumModelTest(TestCase):
    def setUp(self):
        self.test_username = os.getenv("TEST_USERNAME", "u2")
        self.test_password = os.getenv("TEST_PASSWORD", "pwnyabebasss")
        self.user = User.objects.create_user(self.test_username, password=self.test_password)

    def test_str_and_relations(self):
        post = Forum.objects.create(
            user=self.user, title="Judul", description="Isi", tag="ikan"
        )
        reply = Forum.objects.create(
            user=self.user,
            title="Reply Judul Forum",
            description="Balas",
            parent=post,
            tag="kolam"
        )
        self.assertIn("Forum Post", str(post))
        self.assertIn("Reply", str(reply))
        self.assertEqual(reply.parent, post)
        self.assertEqual(post.tag, "ikan")
        self.assertEqual(reply.tag, "kolam")
        self.assertEqual(post.replies.first(), reply)

    def test_vote_properties_and_uniqueness(self):
        post = Forum.objects.create(
            user=self.user, title="Votes", description="Desc", tag="siklus"
        )
        # Create a vote from user
        ForumVote.objects.create(user=self.user, forum=post)
        self.assertEqual(post.upvotes, 1)

        # Create vote from another user
        user2 = User.objects.create_user("u22", password="pwnyabebasss2")
        ForumVote.objects.create(user=user2, forum=post)
        self.assertEqual(post.upvotes, 2)

        # Test uniqueness constraint (user can't vote twice)
        with self.assertRaises(IntegrityError):
            ForumVote.objects.create(user=self.user, forum=post)
