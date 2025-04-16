from typing import List
from ninja import Router
from ninja.responses import Response
from uuid import UUID
from django.contrib.auth.models import User
from forum.models import ForumVote
from forum.schemas import ForumUpdateSchema, ForumOutputSchema, ForumCreateSchema, ForumReplySchema
from forum.repositories.forum_repository import ForumRepository
from ninja_jwt.authentication import JWTAuth
from django.http import Http404, HttpResponse

router = Router()

@router.post("/create", response=ForumOutputSchema, auth=JWTAuth())
def create_forum(request, data: ForumCreateSchema):

    if not request.user.is_authenticated: return Response({"error": "You are not authorized to create this forum post."}, status=403)
   
    parent_forum = None
    if data.parent_id:
        try:
            parent_forum = ForumRepository.get_forum_by_id(UUID(data.parent_id))
        except Exception:
            return Response({
                "error": "Invalid parent forum ID"
            }, status=400)
   
    new_forum = ForumRepository.create_forum(
        user=request.user,
        description=data.description,
        parent=parent_forum
    )
    return new_forum

@router.post("/create_reply", response=ForumReplySchema, auth=JWTAuth())
def create_reply(request, data: ForumCreateSchema):
    # Ensure a parent forum ID is provided since this is a reply.
    if not data.parent_id:
        return Response({"error": "Parent forum ID is required to create a reply."}, status=400)
    
    # Validate that the parent forum exists.
    try:
        parent_forum = ForumRepository.get_forum_by_id(UUID(str(data.parent_id)))
    except Exception:
        return Response({"error": "Invalid parent forum ID"}, status=400)
    
    # Create the reply, associating it with the parent forum.
    reply = ForumRepository.create_forum(
        user=request.user,
        description=data.description,
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
def get_list_forums(request):
    forums = ForumRepository.list_forums()
    return forums

@router.get("/get_by_user", response=List[ForumOutputSchema], auth=JWTAuth())
def get_forums_by_user(request):
    if not request.user.is_authenticated: return Response({"error": "You are not authorized to access this resource."}, status=403)
    forums = ForumRepository.get_forums_by_user(request.user)
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

@router.put("/{forum_id}", response={200: ForumOutputSchema, 403: dict, 404: dict}, auth=JWTAuth())
def update_forum(request, forum_id: UUID, data: ForumUpdateSchema):
    """
    Endpoint untuk memperbarui deskripsi forum.
    """
    try:
        forum = ForumRepository.get_forum_by_id(forum_id)
    except Http404:
        return Response({"error": "Forum not found"}, status=404)
    
    if request.user != forum.user:
        return Response({"error": "You are not authorized to update this forum post."}, status=403)
    
    updated_forum = ForumRepository.update_forum(forum_id, data.description)
    return 200, updated_forum

@router.post("/upvote/{forum_id}", auth=JWTAuth())
def upvote_forum(request, forum_id: UUID):
    forum = ForumRepository.get_forum_by_id(forum_id) 
    ForumRepository.upvote_forum(request.user, forum)
    return HttpResponse(status=204)

@router.post("/downvote/{forum_id}", auth=JWTAuth())
def downvote_forum(request, forum_id: UUID):
    forum = ForumRepository.get_forum_by_id(forum_id)
    ForumRepository.downvote_forum(request.user, forum)
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

