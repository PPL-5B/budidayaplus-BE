from django.test import TestCase
from django.contrib.auth.models import User
from user_profile.models import UserProfile, Worker
from user_profile.services.get_team_service_impl import GetTeamServiceImpl


class GetTeamServiceImplTest(TestCase):
    def setUp(self):
        # Supervisor
        self.supervisor_user = User.objects.create_user(
            username="supervisor", password="password"
        )
        self.supervisor_profile = UserProfile.objects.create(user=self.supervisor_user)

        # Worker 1
        self.worker_user1 = User.objects.create_user(
            username="worker1", password="password"
        )
        self.worker1 = Worker.objects.create(
            user=self.worker_user1,
            assigned_supervisor=self.supervisor_profile,
            image_name=""
        )

        # Worker 2
        self.worker_user2 = User.objects.create_user(
            username="worker2", password="password"
        )
        self.worker2 = Worker.objects.create(
            user=self.worker_user2,
            assigned_supervisor=self.supervisor_profile,
            image_name=""
        )

    def test_get_team_as_supervisor(self):
        team = GetTeamServiceImpl.get_team(self.supervisor_user)
        user_ids = [member.user.id for member in team]
        self.assertIn(self.supervisor_user.id, user_ids)
        self.assertIn(self.worker_user1.id, user_ids)
        self.assertIn(self.worker_user2.id, user_ids)

    def test_get_team_as_worker(self):
        team = GetTeamServiceImpl.get_team(self.worker_user1)
        user_ids = [member.user.id for member in team]
        self.assertIn(self.supervisor_user.id, user_ids)
        self.assertIn(self.worker_user1.id, user_ids)
        self.assertIn(self.worker_user2.id, user_ids)

    def test_get_team_by_username(self):
        team = GetTeamServiceImpl.get_team_by_username("worker1")
        user_ids = [member.user.id for member in team]
        self.assertIn(self.supervisor_user.id, user_ids)

    def test_get_workers_only_list_as_supervisor(self):
        workers = GetTeamServiceImpl.get_workers_only_list(self.supervisor_user)
        usernames = [worker.user.username for worker in workers]
        self.assertIn("worker1", usernames)
        self.assertIn("worker2", usernames)

    def test_get_workers_only_list_as_worker(self):
        workers = GetTeamServiceImpl.get_workers_only_list(self.worker_user1)
        usernames = [worker.user.username for worker in workers]
        self.assertIn("worker1", usernames)
        self.assertIn("worker2", usernames)

    def test_is_in_team_true_as_worker(self):
        result = GetTeamServiceImpl.is_in_team(self.worker_user1, self.supervisor_user)
        self.assertTrue(result)

    def test_is_in_team_true_as_supervisor(self):
        result = GetTeamServiceImpl.is_in_team(self.supervisor_user, self.supervisor_user)
        self.assertTrue(result)

    def test_is_in_team_false(self):
        outsider = User.objects.create_user(username="outsider", password="pass")
        UserProfile.objects.create(user=outsider)
        result = GetTeamServiceImpl.is_in_team(outsider, self.supervisor_user)
        self.assertFalse(result)
