from django.test import TestCase
from django.contrib.auth.models import User
from user_profile.models import UserProfile, Worker
from user_profile.permissions import check_supervisor_permission, check_team_supervisor_permission
from django.core.exceptions import PermissionDenied


class PermissionCheckTest(TestCase):
    def setUp(self):
        # Supervisor user
        self.supervisor = User.objects.create_user(username="supervisor", password="1234", is_staff=True)
        self.supervisor_profile = UserProfile.objects.get(user=self.supervisor)  # from signal

        # Regular (non-staff) user
        self.regular_user = User.objects.create_user(username="user1", password="1234")
        self.regular_profile = UserProfile.objects.create(user=self.regular_user)

        # Worker assigned to supervisor
        self.worker_user = User.objects.create_user(username="worker1", password="1234")
        self.worker = Worker.objects.create(user=self.worker_user, assigned_supervisor=self.supervisor_profile)

    def test_check_supervisor_permission_valid(self):
        result = check_supervisor_permission(self.supervisor)
        self.assertTrue(result)

    def test_check_supervisor_permission_invalid(self):
        with self.assertRaises(PermissionDenied) as ctx:
            check_supervisor_permission(self.regular_user)
        self.assertIn("akses", str(ctx.exception).lower())

    def test_check_team_supervisor_permission_valid(self):
        result = check_team_supervisor_permission(self.supervisor, self.worker_user)
        self.assertTrue(result)

    def test_check_team_supervisor_permission_invalid_not_in_team(self):
        with self.assertRaises(PermissionDenied) as ctx:
            check_team_supervisor_permission(self.supervisor, self.regular_user)
        self.assertIn("akses", str(ctx.exception).lower())

    def test_check_team_supervisor_permission_invalid_not_supervisor(self):
        with self.assertRaises(PermissionDenied) as ctx:
            check_team_supervisor_permission(self.regular_user, self.worker_user)
        self.assertIn("akses", str(ctx.exception).lower())
