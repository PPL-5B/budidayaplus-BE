from uuid import UUID
from typing import Optional, List
from django.shortcuts import get_object_or_404
from forum.models import Forum
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist

class ForumRepository:
    @staticmethod
    def get_forum_by_id(forum_id: UUID) -> Forum:
        return get_object_or_404(Forum, id=forum_id)

    @staticmethod
    def create_forum(user: User, description: str, parent: Optional[Forum] = None) -> Forum:
        return Forum.objects.create(
            user=user,
            description=description,
            parent=parent
        )
    
    @staticmethod
    def delete_forum(forum: Forum):
        forum.delete()

    @staticmethod
    def list_forums() -> List[Forum]:
        return Forum.objects.all()

    @staticmethod
    def get_forums_by_user(user: User) -> List[Forum]:
        return Forum.objects.filter(user=user)
    
    @staticmethod
    def get_latest_forum() -> Optional[Forum]:
        try:
            return Forum.objects.latest('timestamp')
        except ObjectDoesNotExist:
            return None

    @staticmethod
    def get_replies(forum: Forum) -> List[Forum]:
        # Returns all replies for a given forum post.
        return list(forum.replies.all())
