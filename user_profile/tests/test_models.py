import uuid
from django.test import TestCase
from django.contrib.auth.models import User
from user_profile.models import UserProfile, Worker
from user_profile.enums import Role


class UserProfileModelTest(TestCase):
    def setUp(self):
        self.supervisor_user = User.objects.create_user(username="supervisor", password="password")
        self.supervisor_profile = UserProfile.objects.create(user=self.supervisor_user)

        self.worker_user = User.objects.create_user(username="worker", password="password")
        self.worker_profile = Worker.objects.create(
            user=self.worker_user,
            assigned_supervisor=self.supervisor_profile,
            image_name="worker_image.png"
        )

    def test_user_profile_creation(self):
        self.assertIsInstance(self.supervisor_profile.id, uuid.UUID)
        self.assertEqual(self.supervisor_profile.user.username, "supervisor")
        self.assertEqual(self.supervisor_profile.image_name, "")
        self.assertEqual(self.supervisor_profile.role, Role.SUPERVISOR.value)

    def test_worker_profile_creation(self):
        self.assertIsInstance(self.worker_profile.id, uuid.UUID)
        self.assertEqual(self.worker_profile.user.username, "worker")
        self.assertEqual(self.worker_profile.image_name, "worker_image.png")
        self.assertEqual(self.worker_profile.assigned_supervisor, self.supervisor_profile)
        self.assertEqual(self.worker_profile.role, Role.WORKER.value)

    def test_supervisor_has_workers_relation(self):
        workers = list(self.supervisor_profile.workers.all())
        self.assertIn(self.worker_profile, workers)
