import os
from uuid import uuid4
from django.test import TestCase
from django.contrib.auth.models import User
from forum.models import Forum
from forum.schemas import (
    ForumCreateSchema,
    ForumListSchema,
    ForumOutputSchema,
    ForumUpdateSchema,
)


class ForumSchemaTest(TestCase):
    def setUp(self):
        pwd = os.getenv("TEST_USER_PASSWORD", "defaultpass123")
        self.user = User.objects.create_user(
            username="schema_user",
            first_name="Schema",
            last_name="User",
            password=pwd,
        )

    # ------------ ForumCreateSchema ------------
    def test_create_schema_main_and_reply(self):
        main = ForumCreateSchema(
            title="Judul",
            description="Deskripsi",
        )
        self.assertEqual(main.title, "Judul")
        self.assertIsNone(main.parent_id)

        pid = uuid4()
        reply = ForumCreateSchema(description="Balasan", parent_id=pid)
        self.assertIsNone(reply.title)
        self.assertEqual(str(reply.parent_id), str(pid))

    # ------------ ForumUpdateSchema ------------
    def test_update_schema_validation(self):
        ok = ForumUpdateSchema(title="Baru", description="Ubah")
        self.assertEqual(ok.description, "Ubah")

        # None boleh
        self.assertIsNone(ForumUpdateSchema().title)

        # String kosong → error
        with self.assertRaises(ValueError):
            ForumUpdateSchema(title="")
        with self.assertRaises(ValueError):
            ForumUpdateSchema(description="   ")

    # ------------ ForumOutputSchema & List ------------
    def test_output_and_list_schema(self):
        post = Forum.objects.create(
            user=self.user, title="Judul", description="Isi"
        )
        reply = Forum.objects.create(
            user=self.user,
            title="Reply Judul Forum",
            description="Balasan",
            parent=post,
        )

        udata = {
            "id": self.user.id,
            "username": self.user.username,
            "first_name": self.user.first_name,
            "last_name": self.user.last_name,
        }

        payload = {
            "id": post.id,
            "user": udata,
            "title": post.title,
            "description": post.description,
            "timestamp": post.timestamp,
            "parent_id": None,
            "replies": [
                {
                    "id": reply.id,
                    "user": udata,
                    "title": reply.title,
                    "description": reply.description,
                    "timestamp": reply.timestamp,
                }
            ],
            "upvotes": 0,
            "downvotes": 0,
        }
        out = ForumOutputSchema(**payload)
        self.assertEqual(out.replies[0].title, "Reply Judul Forum")

        # List
        lst = ForumListSchema(forums=[payload])
        self.assertEqual(len(lst.forums), 1)
