from ninja import Schema
from pydantic import UUID4
from datetime import datetime
from typing import List
from user_profile.schemas import UserSchema

class UserSchema(Schema):
    id: int
    username: str
    first_name: str
    last_name: str

class ForumCreateSchema(Schema):
    """
    Schema for creating a new Forum entry.
    """
    description: str

class ForumOutputSchema(Schema):
    """
    Schema for reading a Forum entry (output).
    """
    id: UUID4
    user: UserSchema
    description: str
    timestamp: datetime

class ForumListSchema(Schema):
    """
    Schema for listing multiple Forum entries.
    """
    forums: List[ForumOutputSchema]

class ForumUpdateSchema(Schema):
    """
    Schema for updating an existing Forum entry.
    """
    description: str