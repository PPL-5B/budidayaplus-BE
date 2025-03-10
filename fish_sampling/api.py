from ninja import Router
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from cycle.services.cycle_service import CycleService
from ninja.responses import Response
from user_profile.utils import get_supervisor
from .models import FishSampling
from pond.models import Pond
from cycle.models import Cycle
from .schemas import FishSamplingCreateSchema, FishSamplingOutputSchema, FishSamplingList
from ninja_jwt.authentication import JWTAuth
from ninja.errors import HttpError
from datetime import datetime
from django.utils.timezone import make_aware
from django.core.exceptions import ObjectDoesNotExist

DATA_NOT_FOUND = "Data tidak ditemukan"
CYCLE_NOT_ACTIVE = "Siklus tidak aktif"
UNAUTHORIZED_ACCESS = "Anda tidak memiliki akses untuk melihat data ini"

router = Router()

def check_today_fish_sampling(pond, cycle):
    today = datetime.now().date()
    if FishSampling.objects.filter(pond=pond, cycle=cycle, recorded_at__date=today).exists():
        fish_sampling = FishSampling.objects.get(pond=pond, cycle=cycle, recorded_at__date=today)
        fish_sampling.delete()

def check_cycle_active(cycle):
    today = datetime.now().date()
    if not (cycle.start_date <= today <= cycle.end_date):
        raise HttpError(400, CYCLE_NOT_ACTIVE)

@router.post("/{pond_id}/{cycle_id}/", auth=JWTAuth(), response={200: FishSamplingOutputSchema})
def create_fish_sampling(request, pond_id: str, cycle_id: str, payload: FishSamplingCreateSchema):
    pond = get_object_or_404(Pond, pond_id=pond_id)
    reporter = get_object_or_404(User, id=request.auth.id)
    cycle = get_object_or_404(Cycle, id=cycle_id)
    _ = get_supervisor(user=request.auth)

    check_cycle_active(cycle)

    check_today_fish_sampling(pond, cycle)
    
    # Notifikasi
    if payload.fish_weight <= 0 or payload.fish_length <= 0:
        return Response({"error": "Berat dan panjang ikan harus lebih dari 0"}, status=400)

    # Validasi batas maksimum
    if payload.fish_weight > 10 and payload.fish_length > 100:
        return Response({"error": "Berat dan panjang ikan terlalu besar, harap pastikan data benar."}, status=400)
    
    if payload.fish_weight > 10:
        return Response({"error": "Berat ikan lebih dari 10 kg, harap pastikan data benar."}, status=400)

    if payload.fish_length > 100:
        return Response({"error": "Panjang ikan lebih dari 100 cm, harap pastikan data benar."}, status=400)

    fish_sampling = FishSampling.objects.create(
        pond=pond,
        reporter=reporter,
        cycle=cycle,
        recorded_at=make_aware(datetime.now()),
        **payload.dict()
    )

    response_data = {
        "pond_id": str(fish_sampling.pond.pond_id),
        "reporter": {"id": fish_sampling.reporter.id},
        "fish_weight": fish_sampling.fish_weight,
        "fish_length": fish_sampling.fish_length,
        "recorded_at": fish_sampling.recorded_at.isoformat(),
    }

    return Response(response_data, status=200) # Kirim response ke FE

    
@router.get("/{pond_id}/{cycle_id}/latest/", auth=JWTAuth(), response={200: FishSamplingOutputSchema})
def get_latest_fish_sampling(request, pond_id: str, cycle_id: str):
    cycle = Cycle.objects.get(id=cycle_id)
    pond = get_object_or_404(Pond, pond_id=pond_id)

    check_cycle_active(cycle)

    try:
        fish_sampling = FishSampling.objects.filter(pond=pond, cycle=cycle).latest('recorded_at')
    except ObjectDoesNotExist:
        raise HttpError(404, DATA_NOT_FOUND)
    return fish_sampling


@router.get("/{pond_id}/", auth=JWTAuth(), response={200: FishSamplingList})
def list_fish_samplings(request, pond_id: str):
    cycle = CycleService.get_active_cycle(request.auth)
    pond = get_object_or_404(Pond, pond_id=pond_id)

    check_cycle_active(cycle)

    fish_samplings = FishSampling.objects.filter(cycle=cycle, pond=pond).order_by('-recorded_at')
    return {"fish_samplings": fish_samplings, "cycle_id": cycle.id}

