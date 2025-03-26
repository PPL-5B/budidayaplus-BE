from ninja import Router
from ninja.responses import Response
from uuid import UUID
from django.contrib.auth.models import User
from forum.schemas import ForumUpdateSchema, ForumOutputSchema, ForumCreateSchema
from forum.repositories.forum_repository import ForumRepository
from ninja_jwt.authentication import JWTAuth




router = Router()


@router.post("/create", response=ForumOutputSchema, auth=JWTAuth())
def create_forum(request, data: ForumCreateSchema):
    """
    Endpoint untuk membuat forum baru.
    Pengguna harus login untuk bisa membuat postingan forum.
    Jika `parent_id` diberikan, maka postingan ini akan menjadi reply ke forum lain.
    """
    # print("Headers:", request.headers)
    # print("Request user:", request.user)
    # print("Is authenticated:", request.user.is_authenticated)
    # print("User details:", vars(request.user) if request.user else "No user")
    # Check authentication
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