from datetime import datetime, timedelta
from django.test import TestCase
from django.contrib.auth.models import User
from pond.models import Pond
from cycle.models import Cycle
from fish_sampling.models import FishSampling
from django.utils.timezone import make_aware
from fish_sampling.models import FishSampling, FishDeath
from notifications.models import Notification
from notifications.utils import create_notification

class FishSamplingModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='081234567890', password='password')
        self.pond = Pond.objects.create(
            owner = self.user,
            name = 'Test Pond',
            image_name = 'test.jpg',
            length = 1.0,
            width = 1.0,
            depth = 1.0
        )
        starting_date = make_aware(datetime.strptime('2024-09-01', '%Y-%m-%d'))
        ending_date = starting_date + timedelta(days=60)
        self.cycle = Cycle.objects.create(
            supervisor=self.user,
            start_date=starting_date,
            end_date=ending_date
        )
        class FishSamplingModelTest(TestCase):
            def setUp(self):
                self.user = User.objects.create_user(username='081234567890', password='password')
                self.pond = Pond.objects.create(
                    owner=self.user,
                    name='Test Pond',
                    image_name='test.jpg',
                    length=1.0,
                    width=1.0,
                    depth=1.0
                )
                starting_date = make_aware(datetime.strptime('2024-09-01', '%Y-%m-%d'))
                ending_date = starting_date + timedelta(days=60)
                self.cycle = Cycle.objects.create(
                    supervisor=self.user,
                    start_date=starting_date,
                    end_date=ending_date
                )
                self.fish_sampling = FishSampling.objects.create(
                    pond=self.pond,
                    reporter=self.user,
                    cycle=self.cycle,
                    fish_weight=1.5,
                    fish_length=25.0,
                    recorded_at=make_aware(datetime.now())
                )

            def test_str_method(self):
                self.assertEqual(str(self.fish_sampling), str(self.fish_sampling.sampling_id))

        class FishDeathModelTest(TestCase):
            def setUp(self):
                self.user = User.objects.create_user(username='081234567890', password='password')
                self.pond = Pond.objects.create(
                    owner=self.user,
                    name='Test Pond',
                    image_name='test.jpg',
                    length=1.0,
                    width=1.0,
                    depth=1.0
                )
                starting_date = make_aware(datetime.strptime('2024-09-01', '%Y-%m-%d'))
                ending_date = starting_date + timedelta(days=60)
                self.cycle = Cycle.objects.create(
                    supervisor=self.user,
                    start_date=starting_date,
                    end_date=ending_date
                )
                self.fish_death = FishDeath.objects.create(
                    pond=self.pond,
                    reporter=self.user,
                    cycle=self.cycle,
                    death_count=10,
                    recorded_at=make_aware(datetime.now())
                )

            def test_str_method(self):
                self.assertEqual(str(self.fish_death), f"Fish Death Report: {self.fish_death.death_count} deaths")

            def test_notification_creation(self):
                # Assuming there is a Notification model and a create_notification function

                create_notification(self.fish_death)

                notification = Notification.objects.get(content_object=self.fish_death)
                self.assertIsNotNone(notification)
                self.assertEqual(notification.content_object, self.fish_death)
                self.assertEqual(notification.message, f"Fish Death Report: {self.fish_death.death_count} deaths in {self.pond.name}")
