from django.test import TestCase
from django.contrib.auth.models import User
from forum.models import Forum
from forum.schemas import (
    ForumCreateSchema, ForumOutputSchema, ForumUpdateSchema, ForumListSchema
)
import uuid
from datetime import datetime

class ForumSchemaTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='schema_user',
            password='testpass',
            first_name='Schema',
            last_name='User'
        )
        self.forum = Forum.objects.create(
            user=self.user,
            description="Schema output test"
        )

    def test_forum_create_schema(self):
        """Test valid and invalid ForumCreateSchema"""
        data = {"description": "Test forum create schema"}
        schema_instance = ForumCreateSchema(**data)
        self.assertEqual(schema_instance.description, data["description"])
        
        with self.assertRaises(ValueError):
            ForumCreateSchema(description="")  

        with self.assertRaises(ValueError):
            ForumCreateSchema(description="   ")  

    def test_forum_output_schema(self):
        """Test ForumOutputSchema with valid data"""
        user_schema_data = {
            "id": self.user.id,
            "username": self.user.username,
            "first_name": self.user.first_name,
            "last_name": self.user.last_name,
        }
        forum_output_data = {
            "id": uuid.uuid4(),
            "user": user_schema_data,
            "description": self.forum.description,
            "timestamp": self.forum.timestamp,
        }
        schema_instance = ForumOutputSchema(**forum_output_data)
        
        self.assertEqual(schema_instance.user.username, self.user.username)
        self.assertEqual(schema_instance.user.first_name, self.user.first_name)
        self.assertEqual(schema_instance.user.last_name, self.user.last_name)
        self.assertEqual(schema_instance.description, self.forum.description)
        self.assertEqual(schema_instance.timestamp, self.forum.timestamp)

    def test_forum_update_schema(self):
        """Test valid and invalid ForumUpdateSchema"""
        data = {"description": "Updated forum description"}
        schema_instance = ForumUpdateSchema(**data)
        self.assertEqual(schema_instance.description, data["description"])
        
        update_data = {"description": None}
        schema_instance = ForumUpdateSchema(**update_data)
        self.assertIsNone(schema_instance.description)

        with self.assertRaises(ValueError):
            ForumUpdateSchema(description="")  

        with self.assertRaises(ValueError):
            ForumUpdateSchema(description="   ")  

    def test_forum_list_schema(self):
        """Test ForumListSchema with multiple forums"""
        forum2 = Forum.objects.create(
            user=self.user,
            description="Second forum"
        )
 
        user_data = {
            "id": self.user.id,
            "username": self.user.username,
            "first_name": self.user.first_name,
            "last_name": self.user.last_name,
        }
        
        forums_data = [
            {
                "id": self.forum.id,
                "user": user_data,
                "description": self.forum.description,
                "timestamp": self.forum.timestamp,
            },
            {
                "id": forum2.id,
                "user": user_data,
                "description": forum2.description,
                "timestamp": forum2.timestamp,
            }
        ]
        
        list_schema = ForumListSchema(forums=forums_data)
        self.assertEqual(len(list_schema.forums), 2)
        self.assertEqual(list_schema.forums[0].id, self.forum.id)
        self.assertEqual(list_schema.forums[1].description, forum2.description)