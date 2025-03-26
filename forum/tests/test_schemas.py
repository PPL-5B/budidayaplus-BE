from django.test import TestCase
from django.contrib.auth.models import User
from forum.models import Forum
from forum.schemas import ForumCreateSchema, ForumOutputSchema, UserSchema
from datetime import datetime

class ForumSchemaTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='schema_user',
            password='testpass',
            first_name='Schema',
            last_name='User'
        )

    def test_forum_create_schema(self):
        data = {"description": "Test forum create schema"}
        schema_instance = ForumCreateSchema(**data)
        self.assertEqual(schema_instance.description, data["description"])
        self.assertIsNone(schema_instance.parent_id)
        
        parent_id = "3cfb9d12-5bcd-4fda-90e8-4f3e76c47fdf"
        data_with_parent = {"description": "Reply schema", "parent_id": parent_id}
        schema_instance2 = ForumCreateSchema(**data_with_parent)
        self.assertEqual(schema_instance2.description, "Reply schema")
        self.assertEqual(str(schema_instance2.parent_id), parent_id)

    def test_forum_output_schema(self):
        forum = Forum.objects.create(
            user=self.user,
            description="Schema output test"
        )
        reply = Forum.objects.create(
            user=self.user,
            description="This is a reply",
            parent=forum
        )
        user_schema_data = {
            "id": self.user.id,
            "username": self.user.username,
            "first_name": self.user.first_name,
            "last_name": self.user.last_name,
        }
        forum_output_data = {
            "id": forum.id,
            "user": user_schema_data,
            "description": forum.description,
            "timestamp": forum.timestamp,
            "parent_id": None,
            "replies": [{
                "id": reply.id,
                "user": user_schema_data,
                "description": reply.description,
                "timestamp": reply.timestamp,
            }]
        }
        schema_instance = ForumOutputSchema(**forum_output_data)
        expected_user_dict = UserSchema(**user_schema_data).dict()
        actual_user_dict = schema_instance.user.dict()
        self.assertEqual(actual_user_dict, expected_user_dict)
        self.assertEqual(schema_instance.description, forum.description)
        self.assertEqual(schema_instance.id, forum.id)
        self.assertEqual(schema_instance.timestamp, forum.timestamp)
        self.assertIsNone(schema_instance.parent_id)
        self.assertEqual(len(schema_instance.replies), 1)
        self.assertEqual(schema_instance.replies[0].description, reply.description)
        self.assertEqual(schema_instance.replies[0].id, reply.id)
