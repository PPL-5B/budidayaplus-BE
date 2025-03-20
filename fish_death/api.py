from fish_death.models import FishDeath, FishDeathNotification
from fish_death.schemas import FishDeathOutputSchema, FishDeathNotification, FishDeathCreateSchem, FishDeathList
from pond.models import Pond, PondFishAmount
from cycle.models import Cycle
from ninja import Router, Schema
from ninja.errors import HttpError
from ninja.responses import JsonResponse
from ninja_jwt import JWTAuth
from django.utils import timezone
from typing import List, Optional

@router.post("/{pond_id}/{cycle_id}/death/", auth=JWTAuth(), response={200: FishDeathNotification})
def add_fish_death_notification(request, pond_id: str, cycle_id: str, payload: FishDeathNotification):
    # Validate and process the request
    pond = Pond.objects.filter(pond_id=pond_id).first()
    cycle = Cycle.objects.filter(id=cycle_id).first()

    if not pond or not cycle:
        return JsonResponse({"error": "Invalid pond or cycle."}, status=404)

    if not cycle.is_active:
        return JsonResponse({"error": "Cycle is not active."}, status=400)

    fish_death_count = data.get("fish_death_count", 0)
    if fish_death_count <= 0:
        return JsonResponse({"error": "Fish death count must be greater than 0."}, status=400)

    # Update fish amount
    pond_fish_amount = PondFishAmount.objects.filter(pond=pond, cycle=cycle).first()
    if not pond_fish_amount:
        return JsonResponse({"error": "Pond fish amount data not found."}, status=404)

    pond_fish_amount.fish_amount -= fish_death_count
    pond_fish_amount.save()

    # Create fish death record
    fish_death = FishDeath.objects.create(
        pond=pond,
        cycle=cycle,
        reporter=request.user,
        fish_death_count=fish_death_count,
        fish_alive_count=pond_fish_amount.fish_amount,
        recorded_at=timezone.now()
    )

    # Create notification
    FishDeathNotification.objects.create(
        user=pond.owner,
        title="Fish Death Alert",
        message=f"{fish_death_count} fish deaths reported in {pond.name}.",
        created_at=timezone.now()
    )

    return JsonResponse({
        "message": "Fish death data recorded successfully.",
        "id": str(fish_death.id),
        "fish_death_count": fish_death.fish_death_count,
        "fish_alive_count": fish_death.fish_alive_count
    }, status=200)