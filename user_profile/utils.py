from user_profile.models import UserProfile
from django.contrib.auth.models import User
from ninja.errors import HttpError


def get_supervisor(user: User):
    """
    Returns the supervisor of the user if the user is a worker,
    otherwise returns the user themselves
    """
    if user.is_staff:
        return user  # Jika user adalah admin/staff, kembalikan user itu sendiri

    try:
        profile = UserProfile.objects.select_related('worker__assigned_supervisor__user').get(user=user)
        if hasattr(profile, "worker") and profile.worker:
            return profile.worker.assigned_supervisor.user

        return user  # Jika user bukan worker, langsung return user sendiri

    except UserProfile.DoesNotExist:
        raise HttpError(404, "Profile tidak ditemukan")


