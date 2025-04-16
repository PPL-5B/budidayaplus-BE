from django.test import TestCase
from django.contrib.auth.models import User
from forum.models import Forum, ForumVote

class ForumModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser")
        self.user.set_password("testpass") 
        self.user.save()

    def test_create_original_forum_post(self):
        forum = Forum.objects.create(
            user=self.user,
            description="Original forum post"
        )
        self.assertIsNotNone(forum.id)
        self.assertEqual(forum.user, self.user)
        self.assertEqual(forum.description, "Original forum post")
        self.assertIsNotNone(forum.timestamp)
        self.assertIsNone(forum.parent)
        self.assertIn(self.user.username, str(forum))
    
    def test_create_reply_forum_post(self):
        parent_post = Forum.objects.create(
            user=self.user,
            description="Original forum post"
        )
        reply = Forum.objects.create(
            user=self.user,
            description="This is a reply",
            parent=parent_post
        )
        self.assertIsNotNone(reply.id)
        self.assertEqual(reply.parent, parent_post)
        self.assertEqual(reply.description, "This is a reply")
        self.assertIn(reply, list(parent_post.replies.all()))
        self.assertIn("Reply", str(reply))
    
    def test_upvote_and_downvote_count(self):
        forum = Forum.objects.create(user=self.user, description="Forum with votes")

        # Tambah 2 upvotes
        ForumVote.objects.create(user=self.user, forum=forum, vote_choice='up')
        user2 = User.objects.create_user(username="user2", password="pass")
        ForumVote.objects.create(user=user2, forum=forum, vote_choice='up')

        # Tambah 1 downvote
        user3 = User.objects.create_user(username="user3", password="pass")
        ForumVote.objects.create(user=user3, forum=forum, vote_choice='down')

        self.assertEqual(forum.upvotes, 2)
        self.assertEqual(forum.downvotes, 1)
    
    def test_user_cannot_vote_twice_on_same_forum(self):
        forum = Forum.objects.create(user=self.user, description="Forum post")
        ForumVote.objects.create(user=self.user, forum=forum, vote_choice='up')

        with self.assertRaises(Exception):
            ForumVote.objects.create(user=self.user, forum=forum, vote_choice='down')
