import os
from django.test import TestCase
from django.contrib.auth.models import User
from forum.models import Forum, ForumVote


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

    def test_vote_properties_and_unique(self):
        p = Forum.objects.create(
            user=self.user, title="Votes", description="X", tag="siklus"
        )
        ForumVote.objects.create(user=self.user, forum=p, vote_choice="up")
        test_username2 = os.getenv("TEST_USERNAME2", "u22")
        test_password2 = os.getenv("TEST_PASSWORD2", "pwnyabebasss2")
        u2 = User.objects.create_user(test_username2, password=test_password2)
        ForumVote.objects.create(user=u2, forum=p, vote_choice="down")
        self.assertEqual(p.upvotes, 1)
        self.assertEqual(p.downvotes, 1)
        self.assertEqual(p.tag, "siklus")

        with self.assertRaises(Exception):
            ForumVote.objects.create(
                user=self.user, forum=p, vote_choice="down"
            )
