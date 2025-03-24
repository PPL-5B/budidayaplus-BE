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
    def create_forum(user: User, description: str) -> Forum:
        return Forum.objects.create(
            user=user,
            description=description,
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