import json
from uuid import UUID
from typing import Optional, List
from django.shortcuts import get_object_or_404
from forum.models import Forum, ForumVote
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db import models

class ForumRepository:
    @staticmethod
    def get_forum_by_id(forum_id: UUID) -> Forum:
        return get_object_or_404(Forum, id=forum_id)

    @staticmethod
    def create_forum(
        user: User,
        title: str,
        description: str,
        tag: str,
        parent: Optional[Forum] = None,
    ) -> Forum:
        if parent and (title is None or title.strip() == ""):
            title = f"Reply {parent.title} Forum"

        return Forum.objects.create(
            user=user,
            title=title or "",      # fallback agar kolom tidak null
            tag=tag, 
            description=description,
            parent=parent,
        )

    @staticmethod
    def delete_forum(forum: Forum):
        forum.delete()

    @staticmethod
    def list_forums(limit=20, offset=0, parent_id: Optional[UUID] = None):
        """
        Mengambil daftar forum dengan pagination dan filter parent_id.
        Jika parent_id=None, hanya forum utama yang diambil.
        """
        query = Forum.objects.select_related("user")
        if parent_id is None:
            query = query.filter(parent__isnull=True)  # Hanya forum utama
        else:
            query = query.filter(parent_id=parent_id)  # Hanya balasan untuk forum tertentu
        return query.order_by("-timestamp")[offset:offset + limit]
    
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
    def update_forum_by_id(forum_id: UUID, title: str, description: str) -> Forum:
        forum = get_object_or_404(Forum, id=forum_id)
        forum.title = title
        forum.description = description
        forum.save()
        return forum
    
    @staticmethod
    def upvote_forum(user: User, forum: Forum):
        ForumVote.objects.get_or_create(user=user, forum=forum)

    @staticmethod
    def cancel_vote(user: User, forum: Forum):
        ForumVote.objects.filter(user=user, forum=forum).delete()

    @staticmethod
    def get_vote_summary(forum_ids: List[UUID]) -> dict:
        """
        Returns a summary of votes for a list of forums.
        """
        votes = ForumVote.objects.filter(forum_id__in=forum_ids).values("forum_id").annotate(upvotes=models.Count("id"))
        return {vote["forum_id"]: {"upvotes": vote["upvotes"]} for vote in votes}

    @staticmethod
    def search_forums(query: str) -> List[Forum]:
        """
        Search forums by title and description
        """
        return Forum.objects.filter(
            models.Q(title__icontains=query) | 
            models.Q(description__icontains=query),
            parent__isnull=True  
        ).order_by('-timestamp')