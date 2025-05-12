from typing import List
from ninja import Router, Query
from ninja.responses import Response
from uuid import UUID
from django.contrib.auth.models import User
from forum.models import ForumVote
from forum.schemas import ForumUpdateSchema, ForumOutputSchema, ForumCreateSchema, ForumReplySchema
from forum.repositories.forum_repository import ForumRepository
from forum.models import Forum
from ninja_jwt.authentication import JWTAuth
from ninja import Query
from silk.profiling.profiler import silk_profile
from django.http import Http404, HttpResponse, JsonResponse

router = Router()

@router.post("/create", response=ForumOutputSchema, auth=JWTAuth())
def create_forum(request, data: ForumCreateSchema):
    # Post utama harus punya title
    if data.parent_id is None and not data.title:
        return Response({"error": "Title wajib diisi."}, status=400)

    parent_forum = None
    if data.parent_id:
        try:
            parent_forum = ForumRepository.get_forum_by_id(UUID(str(data.parent_id)))
        except Exception:
            return Response({"error": "Invalid parent forum ID"}, status=400)

    new_forum = ForumRepository.create_forum(
        user=request.user,
        title=data.title,
        description=data.description,
        tag=data.tag,
        parent=parent_forum
    )
    return new_forum

@router.post("/create_reply", response=ForumReplySchema, auth=JWTAuth())
def create_reply(request, data: ForumCreateSchema):
    if not data.parent_id:
        return Response({"error": "Parent forum ID is required to create a reply."}, status=400)
    try:
        parent_forum = ForumRepository.get_forum_by_id(UUID(str(data.parent_id)))
    except Exception:
        return Response({"error": "Invalid parent forum ID"}, status=400)

    reply = ForumRepository.create_forum(
        user=request.user,
        title=data.title,               # boleh None
        description=data.description,
        tag=data.tag,
        parent=parent_forum
    )
    return reply


@router.delete("/delete/{forum_id}", auth=JWTAuth())
def delete_forum(request, forum_id: UUID):
    try:
        forum = ForumRepository.get_forum_by_id(forum_id)
    except Http404:
        return Response({"error": "Not Found."}, status=404)

    if forum.user != request.user:
        return Response({"error": "You are not authorized to delete this forum."}, status=403)

    forum.delete()
    return {"message": "Forum deleted successfully."}
  
@router.get("/get_by_id/{forum_id}", response=ForumOutputSchema, auth=JWTAuth())
def get_forum_by_id(request, forum_id: UUID):
    try:
        forum = ForumRepository.get_forum_by_id(forum_id)
        return forum
    except Http404:
        return Response({"error": "Forum not found"}, status=404)

@router.get("/list", response=List[ForumOutputSchema], auth=JWTAuth())
@silk_profile(name="forum_api:list_forums")
def get_list_forums(request, limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0)):
    """
    Endpoint untuk mengambil daftar forum dengan pagination dan optimisasi query.
    """
    forums = ForumRepository.list_forums(limit=limit, offset=offset)
    return forums

@router.get("/get_by_user", response=List[ForumOutputSchema], auth=JWTAuth())
def get_forums_by_user(request):
    forums = ForumRepository.get_forums_by_user(request.user)
    return forums

from silk.profiling.profiler import silk_profile
@silk_profile(name="Profiling Search Forum")
@router.get("/search", response=List[ForumOutputSchema], auth=JWTAuth())
def search_forums(request, query: str = Query(..., description="Search query")):
    if not query.strip():
        return Response({"error": "Search query cannot be empty"}, status=400)
    
    results = ForumRepository.search_forums(query)
    return results

@router.get("/get_by_tag/{tag}", response=List[ForumOutputSchema], auth=JWTAuth())
def get_forums_by_tag(request, tag: str):
    """
    Endpoint to get forums filtered by tag.
    """
    # Validate that the tag is one of the allowed choices
    valid_tags = [tag_choice[0] for tag_choice in Forum.TAG_CHOICES]
    
    if tag not in valid_tags:
        return Response({"error": f"Invalid tag. Tag must be one of: {', '.join(valid_tags)}"}, status=400)
    
    forums = ForumRepository.get_forums_by_tag(tag)
    return forums

@router.get("/get_latest", response=ForumOutputSchema, auth=JWTAuth())
def get_latest_forum(request):
    forum = ForumRepository.get_latest_forum()
    if not forum:
        return Response({"error": "No forums available."}, status=404)
    return forum

@router.get("/get_replies/{forum_id}", response=List[ForumOutputSchema], auth=JWTAuth())
def get_replies(request, forum_id: UUID):
    try:
        forum = ForumRepository.get_forum_by_id(forum_id)
        replies = ForumRepository.get_replies(forum)
        return replies
    except Exception:
        return Response({"error": "Forum not found or invalid forum ID"}, status=404)
    
@router.get("/user_votes", auth=JWTAuth())
def get_votes_by_user(request):
    """
    Mendapatkan semua vote yang diberikan oleh user yang sedang login.
    """
    if not request.user.is_authenticated: return Response({"error": "You are not authorized to access this resource."}, status=403)

    votes = ForumVote.objects.filter(user=request.user).values("forum__id", "forum__description") 
    return JsonResponse({"votes": list(votes)}, safe=False)

@router.put("/{forum_id}", response={200: ForumOutputSchema, 403: dict, 404: dict}, auth=JWTAuth())
def update_forum(request, forum_id: UUID, data: ForumUpdateSchema):
    try:
        forum = ForumRepository.get_forum_by_id(forum_id)
    except Http404:
        return Response({"error": "Forum not found"}, status=404)

    if request.user != forum.user:
        return Response({"error": "You are not authorized to update this forum post."}, status=403)

    updated_forum = ForumRepository.update_forum(
        forum_id,
        title=data.title,
        description=data.description
    )
    return 200, updated_forum

@router.post("/upvote/{forum_id}", auth=JWTAuth())
def upvote_forum(request, forum_id: UUID):
    forum = ForumRepository.get_forum_by_id(forum_id) 
    ForumRepository.upvote_forum(request.user, forum)
    return HttpResponse(status=204)

@router.delete("/cancel_vote/{forum_id}", auth=JWTAuth())
def cancel_vote(request, forum_id: UUID):
    forum = ForumRepository.get_forum_by_id(forum_id)
    ForumRepository.cancel_vote(request.user, forum)
    return HttpResponse(status=204)

@router.get("/vote_summary/{forum_id}", auth=JWTAuth())
def vote_summary(request, forum_id: UUID):
    forum = ForumRepository.get_forum_by_id(forum_id)
    summary = ForumRepository.get_vote_summary(forum)
    
    user_vote = ForumVote.objects.filter(user=request.user, forum=forum).first()
    summary["user_vote"] = user_vote.vote_choice if user_vote else None

    return summary

@router.put("/update/{forum_id}", response=ForumOutputSchema, auth=JWTAuth())
def update_forum(request, forum_id: UUID, data: ForumUpdateSchema):
    try:
        forum = ForumRepository.get_forum_by_id(forum_id)

        if forum.user != request.user:
            return Response({"error": "You are not authorized to update this forum."}, status=403)

        updated_forum = ForumRepository.update_forum_by_id(forum_id, data.title, data.description)
        return updated_forum
    except Http404:
        return Response({"error": "Forum not found."}, status=404)
    except Exception as e:
        return Response({"error": str(e)}, status=500)
