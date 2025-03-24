from django.test import TestCase
from django.contrib.auth.models import User
from forum.models import Forum
from forum.schemas import ForumCreateSchema, ForumOutputSchema

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

    def test_forum_output_schema(self):
        forum = Forum.objects.create(
            user=self.user,
            description="Schema output test"
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
        }
        schema_instance = ForumOutputSchema(**forum_output_data)
        self.assertEqual(schema_instance.user.username, self.user.username)
        self.assertEqual(schema_instance.user.first_name, self.user.first_name)
        self.assertEqual(schema_instance.user.last_name, self.user.last_name)
        self.assertEqual(schema_instance.description, forum.description)
        self.assertEqual(schema_instance.id, forum.id)
        self.assertEqual(schema_instance.timestamp, forum.timestamp)