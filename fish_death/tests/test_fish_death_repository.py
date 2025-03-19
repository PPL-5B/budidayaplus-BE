from django.test import TestCase
from datetime import datetime, timedelta
from django.contrib.auth.models import User
from fish_death.models import FishDeath
from pond.models import Pond
from cycle.models import Cycle
from fish_death.repositories.fish_death_repository import FishDeathRepository

class FishDeathRepositoryTest(TestCase):
    
    def setUp(self):
        date_now = datetime.now()
        start_date = date_now - timedelta(days=30)
        end_date = start_date + timedelta(days=60)

        self.user = User.objects.create_user(username='081234567890', password='password')
        self.pond = Pond.objects.create(
            owner=self.user,
            name='Pond',
            image_name='pond.png',
            length=10.0,
            width=5.0,
            depth=2.0
        )
        self.cycle = Cycle.objects.create(
            supervisor=self.user,
            start_date=start_date,
            end_date=end_date,
        )
        self.fish_death = FishDeath.objects.create(
            pond=self.pond,
            reporter=self.user,
            cycle=self.cycle,
            recorded_at=datetime.now(),
            fish_death_count = 10,
            fish_alive_count = 90,
        )

    def test_get_pond(self):
        pond = FishDeathRepository.get_pond(self.pond.pond_id)
        self.assertEqual(pond, self.pond)
    
    def test_get_cycle(self):
        cycle = FishDeathRepository.get_cycle(self.cycle.id)
        self.assertEqual(cycle, self.cycle)

    def test_get_reporter(self):
        reporter = FishDeathRepository.get_reporter(self.user.id)
        self.assertEqual(reporter, self.user)
    
    def test_get_existing_fish_death(self):
        existing_fish_death = FishDeathRepository.get_existing_fish_death(
            cycle=self.cycle,
            pond=self.pond,
            today=datetime.now().date()
        )
        self.assertEqual(existing_fish_death, self.fish_death)
    
    def test_create_fish_death(self):
        new_fish_death = FishDeathRepository.create_fish_death(
            pond=self.pond,
            reporter=self.user,
            cycle=self.cycle,
            recorded_at=datetime.now(),
            fish_death_count = 20,
            fish_alive_count = 110,
        )
        self.assertIsNotNone(new_fish_death)
        self.assertEqual(new_fish_death.fish_death_count, 20)
        self.assertEqual(new_fish_death.fish_alive_count, 110)
    
    def test_delete_fish_death(self):
        FishDeathRepository.delete_fish_death(self.fish_death)
        with self.assertRaises(FishDeath.DoesNotExist):
            FishDeath.objects.get(id=self.fish_death.id)

    def test_get_fish_death_by_id(self):
        fish_death = FishDeathRepository.get_fish_death_by_id(self.fish_death.id)
        self.assertEqual(fish_death, self.fish_death)
    
    def test_get_latest_fish_death(self):
        latest_sampling = FishDeathRepository.get_latest_fish_death(self.pond, self.cycle)
        self.assertEqual(latest_sampling, self.fish_death)

    def test_list_fish_deaths(self):
        samplings = FishDeathRepository.list_fish_deaths(self.cycle, self.pond)
        self.assertEqual(len(samplings), 1)
        self.assertEqual(samplings[0], self.fish_death)

    def test_get_latest_fish_death_no_result(self):
        self.fish_death.delete()
        latest_sampling = FishDeathRepository.get_latest_fish_death(self.pond, self.cycle)
        self.assertIsNone(latest_sampling)