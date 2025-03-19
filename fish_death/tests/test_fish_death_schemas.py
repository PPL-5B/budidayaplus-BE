from django.test import TestCase
from ninja.testing import TestClient
from django.contrib.auth.models import User
from pond.models import Pond
from cycle.models import Cycle
from fish_death.models import FishDeath
from fish_death.schemas import FishDeathCreateSchema, FishDeathOutputSchema, FishDeathList
from datetime import datetime, timedelta
from pydantic import ValidationError

from user_profile.schemas import UserSchema

class FishDeathSchemaTest(TestCase):
   
    def setUp(self):
        start_time = datetime.strptime('2024-09-01', '%Y-%m-%d')
        end_time = start_time + timedelta(days=60)
        self.user = User.objects.create_user(username='081234567890', password='password')
        self.pond = Pond.objects.create(
            owner=self.user,
            name='Test Pond',
            image_name='test_pond.png',
            length=10.0,
            width=5.0,
            depth=2.0
        )
        self.cycle = Cycle.objects.create(
            supervisor=self.user,
            start_date=start_time,
            end_date=end_time,
        )
        self.fish_death = FishDeath.objects.create(
            pond=self.pond,
            reporter=self.user,
            cycle=self.cycle,
            fish_death_count=10,
            fish_alive_count=90,
            recorded_at=datetime.now(),
        )
        self.second_fish_death = FishDeath.objects.create(
            pond=self.pond,
            reporter=self.user,
            cycle=self.cycle,
            fish_death_count=5,
            fish_alive_count=85,
            recorded_at=datetime.now(),
        )
        
    def test_create_schema_valid_data(self):
        data = {
            "fish_death_count": 10,
            "fish_alive_count": 90,
            "recorded_at": datetime.now()
        }
        schema = FishDeathCreateSchema(**data)
        self.assertEqual(schema.fish_death_count, data["fish_death_count"])
        self.assertEqual(schema.fish_alive_count, data["fish_alive_count"])
        
    def test_create_schema_invalid_death_count(self):
        data = {
            "fish_death_count": "not a number",
            "fish_alive_count": 90,
            "recorded_at": datetime.now()
        }
        with self.assertRaises(ValidationError):
            FishDeathCreateSchema(**data)
            
    def test_create_schema_invalid_alive_count(self):
        data = {
            "fish_death_count": 10,
            "fish_alive_count": "not a number",
            "recorded_at": datetime.now()
        }
        with self.assertRaises(ValidationError):
            FishDeathCreateSchema(**data)
            
    def test_output_schema_from_model(self):
        output_schema = FishDeathOutputSchema(
            id=self.fish_death.id,
            pond_id=self.fish_death.pond.pond_id,
            cycle_id=self.fish_death.cycle.id,
            reporter=self.user,
            fish_death_count=self.fish_death.fish_death_count,
            fish_alive_count=self.fish_death.fish_alive_count,
            recorded_at=self.fish_death.recorded_at,
        )

        output_schema2 = FishDeathOutputSchema(
            id=self.fish_death.id,
            pond_id=self.fish_death.pond.pond_id,
            cycle_id=self.fish_death.cycle.id,
            reporter=self.user,
            fish_death_count=self.fish_death.fish_death_count,
            fish_alive_count=self.fish_death.fish_alive_count,
            recorded_at=self.fish_death.recorded_at,
        )
        
        self.assertEqual(output_schema2.id, self.fish_death.id)
        self.assertEqual(output_schema.fish_death_count, self.fish_death.fish_death_count)
        self.assertEqual(output_schema.fish_alive_count, self.fish_death.fish_alive_count)