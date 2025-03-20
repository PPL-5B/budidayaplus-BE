from ninja import Schema
from datetime import datetime
from pydantic import UUID4
from typing import List
from user_profile.schemas import UserSchema
from typing import Optional

class FishDeathCreateSchema(Schema):
    fish_death_count: int
    # fish_alive_count: int
    # recorded_at: datetime
    fish_alive_count: Optional[int] = None
    recorded_at: Optional[datetime] = None

class FishDeathOutputSchema(Schema):
    id: UUID4
    pond_id: UUID4
    cycle_id: UUID4
    reporter: UserSchema
    recorded_at: datetime
    fish_death_count: int
    fish_alive_count: int

class FishDeathList(Schema):
    fish_deaths: List[FishDeathOutputSchema]
    cycle_id: UUID4
