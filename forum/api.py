from ninja import Router
from uuid import UUID
from django.http import Http404
from django.contrib.auth.models import User
from forum.schemas import ForumUpdateSchema, ForumOutputSchema
from forum.repositories.forum_repository import ForumRepository
from django.shortcuts import get_object_or_404

router = Router()

@router.put("/{forum_id}", response=ForumOutputSchema)
def update_forum(request, forum_id: UUID, data: ForumUpdateSchema):
    """
    Endpoint untuk memperbarui deskripsi forum.
    """
    forum = ForumRepository.get_forum_by_id(forum_id)
    
    if request.user != forum.user:
        return {"error": "You are not authorized to update this forum post."}, 403
    
    updated_forum = ForumRepository.update_forum(forum_id, data.description)
    return updated_forum
