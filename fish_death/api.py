from ninja import Router
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from ninja.responses import Response
from ninja.errors import HttpError
from ninja_jwt.authentication import JWTAuth
from datetime import datetime
from django.utils.timezone import make_aware
from types import SimpleNamespace

from pond.models import Pond
from cycle.models import Cycle, PondFishAmount
from user_profile.utils import get_supervisor

from fish_death.models import FishDeath
from fish_death.schemas import FishDeathCreateSchema, FishDeathOutputSchema, FishDeathList
from fish_death.services.fish_death_service import FishDeathService
from fish_death.repositories.fish_death_repository import FishDeathRepository

CYCLE_NOT_ACTIVE = "Siklus tidak aktif"
DATA_NOT_FOUND = "Data tidak ditemukan"
UNAUTHORIZED_ACCESS = "Anda tidak memiliki akses untuk melihat data ini"
INVALID_FISH_DEATH_COUNT = "Input jumlah kematian ikan tidak valid"

router = Router()

# Instantiate the repository and service for fish death.
fish_death_repository = FishDeathRepository()
fish_death_service = FishDeathService(repository=fish_death_repository)

@router.post("/{pond_id}/{cycle_id}/", auth=JWTAuth(), response={200: FishDeathOutputSchema})
def create_fish_death(request, pond_id: str, cycle_id: str, payload: FishDeathCreateSchema):
    """
    Create a new fish death record.
    The payload from the user is expected to include only fish_death_count.
    Other fields (recorded_at, fish_alive_count) are set by the system.
    The fish_alive_count is retrieved from the corresponding PondFishAmount record.
    """
    pond = get_object_or_404(Pond, pond_id=pond_id)
    reporter = get_object_or_404(User, id=request.auth.id)
    cycle = get_object_or_404(Cycle, id=cycle_id)
    _ = get_supervisor(user=request.auth)

    today = datetime.now().date()
    if not (cycle.start_date <= today <= cycle.end_date):
        raise HttpError(400, CYCLE_NOT_ACTIVE)
    
    # Validate fish_death_count. It should not be negative.
    if payload.fish_death_count < 0:
        raise HttpError(400, INVALID_FISH_DEATH_COUNT)

    # # Retrieve fish_alive_count from the PondFishAmount model attached to the pond and cycle.
    # try:
    #     pond_fish_amount = PondFishAmount.objects.get(pond=pond, cycle=cycle)
    #     fish_alive_count = pond_fish_amount.fish_amount
    # except PondFishAmount.DoesNotExist:
    #     fish_alive_count = 0

    full_payload = {
        "fish_death_count": payload.fish_death_count,
        "recorded_at": make_aware(datetime.now()),
    }
    payload_obj = SimpleNamespace(**full_payload)

    fish_death = fish_death_service.create_fish_death(pond_id, cycle_id, reporter.id, payload_obj)

    response_data = {
        "id": fish_death.id,
        "pond_id": str(fish_death.pond.pond_id),
        "cycle_id": str(fish_death.cycle.id),
        "reporter": {"id": fish_death.reporter.id},
        "recorded_at": fish_death.recorded_at.isoformat(),
        "fish_death_count": fish_death.fish_death_count,
        "fish_alive_count": fish_death.fish_alive_count,
    }

    return Response(response_data, status=200)

@router.get("/{pond_id}/{cycle_id}/latest/", auth=JWTAuth(), response={200: FishDeathOutputSchema})
def get_latest_fish_death(request, pond_id: str, cycle_id: str):
    """
    Retrieve the latest fish death record for the given pond and cycle.
    """
    cycle = get_object_or_404(Cycle, id=cycle_id)
    pond = get_object_or_404(Pond, pond_id=pond_id)

    fish_death = fish_death_service.get_latest_fish_death(cycle_id, pond_id, request.auth)
    return fish_death

@router.get("/{pond_id}/", auth=JWTAuth(), response={200: FishDeathList})
def list_fish_deaths(request, pond_id: str):
    """
    List all fish death records for the active cycle.
    """
    data = fish_death_service.list_fish_deaths(pond_id, request.auth)
    return data
