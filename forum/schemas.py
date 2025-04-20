from ninja import Schema
from pydantic import UUID4, Field, validator  
from datetime import datetime
from typing import List, Optional
from user_profile.schemas import UserSchema

class ForumCreateSchema(Schema):
    """
    Schema for creating a new Forum entry.
    Optionally includes a parent_id to indicate this post is a reply.
    """
    description: str
    parent_id: Optional[UUID4] = None

class ForumReplySchema(Schema):
    """
    Schema for a simple reply representation.
    """
    id: UUID4
    user: UserSchema
    description: str
    timestamp: datetime

class ForumOutputSchema(Schema):
    """
    Schema for reading a Forum entry (output).
    Includes parent_id (if any) and a list of replies.
    """
    id: UUID4
    user: UserSchema
    description: str
    timestamp: datetime
    parent_id: Optional[UUID4] = None
    replies: List[ForumReplySchema] = []
    upvotes: int
    downvotes: int

class ForumListSchema(Schema):
    """
    Schema for listing multiple Forum entries.
    """
    forums: List[ForumOutputSchema]

class ForumUpdateSchema(Schema):
    """
    Schema for updating an existing Forum entry.
    """
    description: Optional[str] = Field(None, min_length=1)

    @validator('description')
    def description_not_empty(cls, v):
        if v is not None and not v.strip():
            raise ValueError('Description cannot be empty')
        return v