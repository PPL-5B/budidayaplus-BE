from django.test import TestCase
from user_profile.enums import Role


class RoleEnumTest(TestCase):
    def test_enum_values(self):
        self.assertEqual(Role.WORKER.value, "worker")
        self.assertEqual(Role.SUPERVISOR.value, "supervisor")

    def test_enum_names(self):
        self.assertEqual(Role.WORKER.name, "WORKER")
        self.assertEqual(Role.SUPERVISOR.name, "SUPERVISOR")

    def test_choices_method(self):
        expected = [("worker", "WORKER"), ("supervisor", "SUPERVISOR")]
        self.assertEqual(Role.choices(), expected)
