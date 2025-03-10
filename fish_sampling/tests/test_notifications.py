from django.utils.timezone import make_aware
from fish_sampling.models import FishSampling, FishDeath
from notifications.models import Notification
from notifications.utils import create_notification

class FishDeathNotificationTest(TestCase):
    def test_create_fish_death_notification(self):
        fish_sampling = FishSampling.objects.create(
            species='Tilapia',
            location='Pond A',
            date=now()
        )
        fish_death = FishDeath.objects.create(
            sampling=fish_sampling,
            count=10,
            date=now()
        )
        notification = create_notification(fish_death)
        self.assertIsInstance(notification, Notification)
        self.assertEqual(notification.title, 'Fish Death Alert')
        self.assertIn('10 Tilapia deaths', notification.message)

if __name__ == '__main__':
    unittest.main()