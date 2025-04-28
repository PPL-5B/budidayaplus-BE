from uuid import UUID
from typing import Optional, List
from django.shortcuts import get_object_or_404
from forum.models import Forum, ForumVote
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist


class ForumRepository:
    @staticmethod
    def get_forum_by_id(forum_id: UUID) -> Forum:
        return get_object_or_404(Forum, id=forum_id)

    @staticmethod
    def create_forum(
        user: User,
        title: str | None,
        description: str,
        tag: str,
        parent: Optional[Forum] = None,
    ) -> Forum:
        if parent and (title is None or title.strip() == ""):
            title = f"Reply {parent.title} Forum"

        return Forum.objects.create(
            user=user,
            title=title or "",      # fallback agar kolom tidak null
            description=description,
            tag=tag,
            parent=parent,
        )

    @staticmethod
    def delete_forum(forum: Forum):
        forum.delete()

    # @staticmethod
    # def list_forums() -> List[Forum]:
    #     return Forum.objects.all()

    @staticmethod
    def list_forums(limit=20, offset=0):
        return Forum.objects.select_related("user") \
            .order_by("-timestamp")[offset:offset + limit]
    
    @staticmethod
    def get_forums_by_user(user: User) -> List[Forum]:
        return Forum.objects.filter(user=user)

    @staticmethod
    def get_forums_by_tag(tag: str) -> List[Forum]:
        """
        Gets all forums with the specified tag.
        """
        return Forum.objects.filter(tag=tag)

    @staticmethod
    def get_latest_forum() -> Optional[Forum]:
        try:
            return Forum.objects.latest('timestamp')
        except ObjectDoesNotExist:
            return None

    @staticmethod
    def get_replies(forum: Forum) -> List[Forum]:
        return list(forum.replies.all())

    @staticmethod
    def update_forum(
        forum_id: UUID, 
        title: str | None = None, 
        description: str | None = None,
        tag: str | None = None
    ) -> Forum:
        forum = get_object_or_404(Forum, id=forum_id)
        if title is not None:
            forum.title = title
        if description is not None:
            forum.description = description
        if tag is not None:
            forum.tag = tag
        forum.save()
        return forum

    @staticmethod
    def upvote_forum(user: User, forum: Forum):
        ForumVote.objects.update_or_create(
            user=user,
            forum=forum,
            defaults={'vote_choice': 'up'}
        )
    
    @staticmethod
    def downvote_forum(user: User, forum: Forum):
        ForumVote.objects.update_or_create(
            user=user,
            forum=forum,
            defaults={'vote_choice': 'down'}
        )

    @staticmethod
    def cancel_vote(user: User, forum: Forum):
        ForumVote.objects.filter(user=user, forum=forum).delete()

    @staticmethod
    def get_vote_summary(forum: Forum) -> dict:
        return {
            'upvotes': forum.upvotes,
            'downvotes': forum.downvotes,
        }