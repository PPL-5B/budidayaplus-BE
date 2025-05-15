from datetime import datetime, timedelta
from django.test import TestCase
from django.contrib.auth.models import User
from pond.models import Pond
from cycle.models import Cycle
from fish_death.models import FishDeath

class FishDeathModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.now = datetime.now()
        cls.user = User.objects.create_user(username='081234567890', password='password')
        cls.pond = Pond.objects.create(
            owner=cls.user,
            name='Test Pond',
            image_name='test.jpg',
            length=1.0,
            width=1.0,
            depth=1.0
        )
        starting_date = datetime.strptime('2024-09-01', '%Y-%m-%d')
        ending_date = starting_date + timedelta(days=60)
        cls.cycle = Cycle.objects.create(
            supervisor=cls.user,
            start_date=starting_date,
            end_date=ending_date
        )
        cls.fish_death = FishDeath.objects.create(
            pond=cls.pond,
            reporter=cls.user,
            cycle=cls.cycle,
            recorded_at=cls.now,
            fish_death_count=10,
            fish_alive_count=90,
        )

    def test_str_method_returns_id(self):
        """Should return ID as string representation of FishDeath"""
        self.assertEqual(str(self.fish_death), str(self.fish_death.id))
