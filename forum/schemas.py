from ninja import Schema
from pydantic import UUID4, Field, validator
from datetime import datetime
from typing import List, Optional
from user_profile.schemas import UserSchema


class ForumCreateSchema(Schema):
    """
    Schema untuk membuat Forum/Reply.
    - title wajib diisi jika parent_id = None (post utama).
    """
    title: Optional[str] = Field(None, max_length=255)
    description: str
    parent_id: Optional[UUID4] = None
    tag: str = Field(..., description="Tag must be one of: ikan, kolam, siklus, budidayaplus")


class ForumReplySchema(Schema):
    id: UUID4
    user: UserSchema
    description: str
    timestamp: datetime
    title: Optional[str] = None
    tag: str


class ForumOutputSchema(Schema):
    id: UUID4
    user: UserSchema
    title: Optional[str] = None
    description: str
    tag: str
    timestamp: datetime
    parent_id: Optional[UUID4] = None
    replies: List[ForumReplySchema] = []
    upvotes: int
    downvotes: int


class ForumListSchema(Schema):
    forums: List[ForumOutputSchema]


class ForumUpdateSchema(Schema):
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, min_length=1)
    tag: Optional[str] = Field(None, description="Tag must be one of: ikan, kolam, siklus, budidayaplus")

    @validator('title', 'description')
    def not_empty(cls, v):
        if v is not None and not v.strip():
            raise ValueError('Field tidak boleh kosong')
        return v