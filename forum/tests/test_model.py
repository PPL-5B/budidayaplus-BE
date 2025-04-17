import os
from django.test import TestCase
from django.contrib.auth.models import User
from forum.models import Forum, ForumVote


class ForumModelTest(TestCase):
    def setUp(self):
        pwd = os.getenv("TEST_USER_PASSWORD", "defaultpass123")
        self.user = User.objects.create_user("model", password=pwd)

    def test_str_and_relations(self):
        post = Forum.objects.create(
            user=self.user, title="Judul", description="Isi"
        )
        reply = Forum.objects.create(
            user=self.user,
            title="Reply Judul Forum",
            description="Balas",
            parent=post,
        )
        self.assertIn("Forum Post", str(post))
        self.assertIn("Reply", str(reply))
        self.assertEqual(reply.parent, post)

    def test_vote_properties_and_unique(self):
        p = Forum.objects.create(
            user=self.user, title="Votes", description="X"
        )
        ForumVote.objects.create(user=self.user, forum=p, vote_choice="up")
        u2 = User.objects.create_user("u2", password="123")
        ForumVote.objects.create(user=u2, forum=p, vote_choice="down")
        self.assertEqual(p.upvotes, 1)
        self.assertEqual(p.downvotes, 1)

        with self.assertRaises(Exception):
            ForumVote.objects.create(
                user=self.user, forum=p, vote_choice="down"
            )
