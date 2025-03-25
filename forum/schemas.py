from ninja import Schema
from pydantic import UUID4, Field, validator  # Perhatikan impor Field dari pydantic
from datetime import datetime
from typing import List, Optional
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
    description: str = Field(..., min_length=1) 

    @validator('description')
    def description_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Description cannot be empty')
        return v

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
    description: Optional[str] = Field(None, min_length=1)

    @validator('description')
    def description_not_empty(cls, v):
        if v is not None and not v.strip():
            raise ValueError('Description cannot be empty')
        return v