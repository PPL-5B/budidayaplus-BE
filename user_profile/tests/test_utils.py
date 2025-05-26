from django.test import TestCase
from django.contrib.auth.models import User
from user_profile.models import UserProfile, Worker
from user_profile.utils import get_supervisor 
from ninja.errors import HttpError


class GetSupervisorTest(TestCase):
    def setUp(self):
        # Supervisor
        self.supervisor_user = User.objects.create_user(
            username="supervisor", password="password", is_staff=False
        )
        self.supervisor_profile, _ = UserProfile.objects.get_or_create(user=self.supervisor_user)

        # Worker
        self.worker_user = User.objects.create_user(
            username="worker", password="password", is_staff=False
        )
        self.worker = Worker.objects.create(
            user=self.worker_user,
            assigned_supervisor=self.supervisor_profile,
            image_name=""
        )
        self.worker_profile = UserProfile.objects.get(user=self.worker_user)

        # Staff (admin)
        self.staff_user = User.objects.create_user(
            username="admin", password="password", is_staff=True
        )
        self.staff_profile, _ = UserProfile.objects.get_or_create(user=self.staff_user)

        # Regular user
        self.regular_user = User.objects.create_user(
            username="regular", password="password"
        )
        self.regular_profile, _ = UserProfile.objects.get_or_create(user=self.regular_user)


    def test_get_supervisor_for_worker(self):
        supervisor = get_supervisor(self.worker_user)
        self.assertEqual(supervisor, self.supervisor_user)

    def test_get_supervisor_for_staff_user(self):
        supervisor = get_supervisor(self.staff_user)
        self.assertEqual(supervisor, self.staff_user)

    def test_get_supervisor_for_regular_user(self):
        supervisor = get_supervisor(self.regular_user)
        self.assertEqual(supervisor, self.regular_user)

    def test_get_supervisor_profile_not_found(self):
        ghost_user = User.objects.create_user(username="ghost", password="123456")
        with self.assertRaises(HttpError) as ctx:
            get_supervisor(ghost_user)
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertEqual(ctx.exception.message, "Profile tidak ditemukan")