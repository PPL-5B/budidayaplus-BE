from datetime import datetime
from ninja.errors import HttpError
from fish_death.repositories.fish_death_repository import FishDeathRepository
from fish_death.schemas import FishDeathCreateSchema
from fish_death.models import FishDeath
from pond.models import Pond
from cycle.models import Cycle
from cycle.repositories.cycle_repo import CycleRepo
from user_profile.utils import get_supervisor


class FishDeathService:
    DATA_NOT_FOUND = "Data tidak ditemukan"
    INVALID_FISH_DEATH_COUNT = "Input jumlah kematian ikan tidak valid"
    UNAUTHORIZED_ACCESS = "Anda tidak memiliki akses untuk melihat data ini"


    fish_death_target = {i: {'fish_death_count': i} for i in range(0, 101)}  # Targets for fish death count from 0 to 100


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


        target_fish_death_count = self.fish_death_target.get(1, {}).get('fish_death_count', 0)
        fish_death.target_fish_death_count = target_fish_death_count


        return fish_death


    def get_latest_fish_death(self, cycle_id: str, pond_id: str, user) -> FishDeath:
        cycle = self.repository.get_cycle(cycle_id)
        pond = self.repository.get_pond(pond_id)


        self.check_cycle_active(cycle)


        fish_death = self.repository.get_latest_fish_death(pond, cycle)
        if fish_death is None:
            raise HttpError(404, self.DATA_NOT_FOUND)


        try:
            self.authorize_user(user, pond)
        except:
            raise HttpError(401, self.UNAUTHORIZED_ACCESS)


        target_fish_death_count = self.fish_death_target.get(1, {}).get('fish_death_count', 0)
        fish_death.target_fish_death_count = target_fish_death_count


        return fish_death


    def list_fish_deaths(self, pond_id: str, user):
        cycle = CycleRepo.get_active_cycle(get_supervisor(user))
        try:
            pond = self.repository.get_pond(pond_id)
        except:
            raise HttpError(404, self.DATA_NOT_FOUND)


        if self.authorize_user(user, pond):
            raise HttpError(401, self.UNAUTHORIZED_ACCESS)
        if cycle is None:
            raise HttpError(404, "Cycle not active")


        fish_deaths = self.repository.list_fish_deaths(cycle, pond)


        for index, fish_death in enumerate(fish_deaths, 1):
            target_fish_death_count = self.fish_death_target.get(index, self.fish_death_target.get(1, {})).get('fish_death_count', 0)
            fish_death.target_fish_death_count = target_fish_death_count


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


        if existing_fish_death:
            self.repository.delete_fish_death(existing_fish_death)


        try:
            fish_death = self.repository.create_fish_death(
                pond=pond,
                reporter=reporter,
                cycle=cycle,
                recorded_at=payload.recorded_at,
                fish_death_count=payload.fish_death_count,
                fish_alive_count=payload.fish_alive_count
            )
        except ValueError:
            raise HttpError(400, self.INVALID_FISH_DEATH_COUNT)


        target_fish_death_count = self.fish_death_target.get(1, {}).get('fish_death_count', 0)
        fish_death.target_fish_death_count = target_fish_death_count


        return fish_death



