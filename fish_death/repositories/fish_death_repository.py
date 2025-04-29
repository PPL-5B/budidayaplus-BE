from datetime import date
from typing import Optional
from django.shortcuts import get_object_or_404
from fish_death.models import FishDeath
from pond.models import Pond
from cycle.models import Cycle
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.core.exceptions import ObjectDoesNotExist

class FishDeathRepository:
    @staticmethod
    def get_pond(pond_id: str) -> Pond:
        return get_object_or_404(Pond, pond_id=pond_id)
    
    @staticmethod
    def get_cycle(cycle_id: str) -> Cycle:
        return get_object_or_404(Cycle, id=cycle_id)
    
    @staticmethod
    def get_reporter(user_id: int) -> User:
        return get_object_or_404(User, id=user_id)

    @staticmethod
    def get_fish_death_by_id(id: str) -> FishDeath:
        return get_object_or_404(FishDeath, id=id)
    
    @staticmethod
    def get_existing_fish_death(cycle: Cycle, pond: Pond, today: date) -> Optional[FishDeath]:
        return FishDeath.objects.select_related("pond", "cycle", "reporter").filter(
            cycle=cycle, pond=pond, recorded_at__date=today
        ).first()
    
    @staticmethod
    def create_fish_death(pond: Pond, reporter: User, cycle: Cycle, recorded_at: date, 
                          fish_death_count: int, fish_alive_count: int) -> FishDeath:
        return FishDeath.objects.create(
            pond=pond,
            reporter=reporter,
            cycle=cycle,
            recorded_at=recorded_at,
            fish_death_count=fish_death_count,
            fish_alive_count=fish_alive_count,
        )
    
    @staticmethod
    def delete_fish_death(fish_death: FishDeath):
        fish_death.delete()

    @staticmethod
    def get_latest_fish_death(pond: Pond, cycle: Cycle) -> Optional[FishDeath]:
        try:
            return FishDeath.objects.select_related("pond", "cycle", "reporter").filter(
                pond=pond, cycle=cycle
            ).latest('recorded_at')
        except ObjectDoesNotExist:
            return None
    
    @staticmethod
    def list_fish_deaths(cycle: Cycle, pond: Pond):
        return FishDeath.objects.filter(cycle=cycle, pond=pond)
