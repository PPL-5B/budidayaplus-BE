from datetime import datetime
from ninja.errors import HttpError
from fish_death.repositories.fish_death_repository import FishDeathRepository
from fish_death.schemas import FishDeathCreateSchema
from fish_death.models import FishDeath
from pond.models import Pond
from cycle.models import Cycle
from cycle.repositories.cycle_repo import CycleRepo
from user_profile.utils import get_supervisor
from django.core.exceptions import ObjectDoesNotExist 
from cycle.models import Cycle, PondFishAmount

class FishDeathService:
    DATA_NOT_FOUND = "Data tidak ditemukan"
    INVALID_FISH_DEATH_COUNT = "Input jumlah kematian ikan tidak valid"
    UNAUTHORIZED_ACCESS = "Anda tidak memiliki akses untuk melihat data ini"

    def __init__(self, repository: FishDeathRepository):
        self.repository = repository

    def check_cycle_active(self, cycle: Cycle):
        today = datetime.now().date()
        if not (cycle.start_date <= today <= cycle.end_date):
            raise HttpError(400, self.DATA_NOT_FOUND)

    def authorize_user(self, user, pond: Pond):
        supervisor = get_supervisor(user)
        if pond.owner != supervisor:
            raise HttpError(401, self.UNAUTHORIZED_ACCESS)

    def get_fish_death(self, cycle_id: str, pond_id: str, fish_death_id: str, user) -> FishDeath:
        cycle = self.repository.get_cycle(cycle_id)
        pond = self.repository.get_pond(pond_id)
        fish_death = self.repository.get_fish_death_by_id(fish_death_id)
        self.check_cycle_active(cycle)

        if fish_death.cycle != cycle or fish_death.pond != pond:
            raise HttpError(404, self.DATA_NOT_FOUND)

        self.authorize_user(user, pond)
        return fish_death

    def get_latest_fish_death(self, cycle_id: str, pond_id: str, user) -> FishDeath:
        cycle = self.repository.get_cycle(cycle_id)
        pond = self.repository.get_pond(pond_id)
        self.check_cycle_active(cycle)
        fish_death = self.repository.get_latest_fish_death(pond, cycle)

        if fish_death is None:
            raise HttpError(404, self.DATA_NOT_FOUND)

        self.authorize_user(user, pond)
        return fish_death

    def list_fish_deaths(self, pond_id: str, user):
        cycle = CycleRepo.get_active_cycle(get_supervisor(user))

        try:
            pond = self.repository.get_pond(pond_id)
        except ObjectDoesNotExist:
            raise HttpError(404, self.DATA_NOT_FOUND)

        if self.authorize_user(user, pond):
            raise HttpError(401, self.UNAUTHORIZED_ACCESS)
        if cycle is None:
            raise HttpError(404, "Cycle not active")

        fish_deaths = self.repository.list_fish_deaths(cycle, pond)
        return {
            'fish_deaths': fish_deaths,
            'cycle_id': cycle.id
        }

    def create_fish_death(self, pond_id: str, cycle_id: str, reporter_id: int, payload: FishDeathCreateSchema) -> FishDeath:
        pond = self.repository.get_pond(pond_id)
        reporter = self.repository.get_reporter(reporter_id)
        cycle = self.repository.get_cycle(cycle_id)
        today = datetime.now().date()
        existing_fish_death = self.repository.get_existing_fish_death(cycle, pond, today)

        latest = self.repository.get_latest_fish_death(pond, cycle)

        pond_fish_amount = PondFishAmount.objects.get(pond=pond, cycle=cycle)
        fish_seed = pond_fish_amount.fish_amount
        current_alive = latest.fish_alive_count if latest else fish_seed

        if payload.fish_death_count > current_alive:
            raise HttpError(400, f"Jumlah ikan mati melebihi jumlah ikan bertahan ({current_alive} ekor).")

        if existing_fish_death:
            self.repository.delete_fish_death(existing_fish_death)
        
        if latest:
             fish_alive = max(latest.fish_alive_count - payload.fish_death_count, 0)
        else:
            pond_fish_amount = PondFishAmount.objects.get(pond=pond, cycle=cycle)
            fish_alive = max(pond_fish_amount.fish_amount - payload.fish_death_count, 0)

        try:
            fish_death = self.repository.create_fish_death(
                pond=pond,
                reporter=reporter,
                cycle=cycle,
                recorded_at=payload.recorded_at,
                fish_death_count=payload.fish_death_count,
                fish_alive_count=fish_alive
            )
        except ValueError:
            raise HttpError(400, self.INVALID_FISH_DEATH_COUNT)

        return fish_death