import unittest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from ninja.errors import HttpError
from fish_death.repositories.fish_death_repository import FishDeathRepository
from fish_death.schemas import FishDeathCreateSchema
from fish_death.models import FishDeath
from fish_death.services.fish_death_service import FishDeathService
from pond.models import Pond
from cycle.models import Cycle
from django.core.exceptions import ObjectDoesNotExist


class TestFishDeathService(unittest.TestCase):
    def setUp(self):
        self.repository = Mock(spec=FishDeathRepository)
        self.service = FishDeathService(self.repository)
        self.today = datetime.now().date()

        self.active_cycle = Mock(spec=Cycle, id="cycle-1", start_date=self.today - timedelta(days=30), end_date=self.today + timedelta(days=30))
        self.inactive_cycle = Mock(spec=Cycle, id="cycle-2", start_date=self.today - timedelta(days=30), end_date=self.today - timedelta(days=1))

        self.pond = Mock(spec=Pond, id="pond-1", owner="owner-1")
        self.user = Mock(id="user-1")
        self.reporter = Mock(id=1)

        self.fish_death = Mock(spec=FishDeath, id="fish-death-1", pond=self.pond, cycle=self.active_cycle, fish_death_count=5, fish_alive_count=95, recorded_at=self.today)

    def test_check_cycle_active_success(self):
        self.service.check_cycle_active(self.active_cycle)

    def test_check_cycle_active_failure(self):
        with self.assertRaises(HttpError) as context:
            self.service.check_cycle_active(self.inactive_cycle)
        self.assertEqual(context.exception.status_code, 400)
        self.assertEqual(context.exception.message, self.service.DATA_NOT_FOUND)

    @patch('fish_death.services.fish_death_service.get_supervisor', return_value="owner-1")
    def test_authorize_user_success(self, mock_get_supervisor):
        self.service.authorize_user(self.user, self.pond)
        mock_get_supervisor.assert_called_once_with(self.user)

    @patch('fish_death.services.fish_death_service.get_supervisor', return_value="other-owner")
    def test_authorize_user_failure(self, mock_get_supervisor):
        with self.assertRaises(HttpError) as context:
            self.service.authorize_user(self.user, self.pond)
        self.assertEqual(context.exception.status_code, 401)
        self.assertEqual(context.exception.message, self.service.UNAUTHORIZED_ACCESS)
        mock_get_supervisor.assert_called_once_with(self.user)

    @patch('fish_death.services.fish_death_service.get_supervisor', return_value="owner-1")
    def test_get_fish_death_success(self, mock_get_supervisor):
        self.repository.get_cycle.return_value = self.active_cycle
        self.repository.get_pond.return_value = self.pond
        self.repository.get_fish_death_by_id.return_value = self.fish_death

        result = self.service.get_fish_death("cycle-1", "pond-1", "fish-death-1", self.user)
        self.assertEqual(result, self.fish_death)

    def test_get_fish_death_wrong_cycle_or_pond(self):
        self.fish_death.cycle.id = "other-cycle"
        self.repository.get_cycle.return_value = self.active_cycle
        self.repository.get_pond.return_value = self.pond
        self.repository.get_fish_death_by_id.return_value = self.fish_death

        with self.assertRaises(HttpError) as context:
            self.service.get_fish_death("cycle-1", "pond-1", "fish-death-1", self.user)
        self.assertEqual(context.exception.status_code, 404)

    @patch('fish_death.services.fish_death_service.get_supervisor', return_value="owner-1")
    def test_get_latest_fish_death_not_found(self, mock_get_supervisor):
        self.repository.get_cycle.return_value = self.active_cycle
        self.repository.get_pond.return_value = self.pond
        self.repository.get_latest_fish_death.return_value = None

        with self.assertRaises(HttpError) as context:
            self.service.get_latest_fish_death("cycle-1", "pond-1", self.user)
        self.assertEqual(context.exception.status_code, 404)

    @patch('fish_death.services.fish_death_service.get_supervisor', return_value="owner-1")
    @patch('fish_death.services.fish_death_service.PondFishAmount.objects.get')
    def test_create_fish_death_success(self, mock_get_amount, mock_get_supervisor):
        schema = FishDeathCreateSchema(recorded_at=self.today, fish_death_count=5)

        mock_get_amount.return_value.fish_amount = 100
        self.repository.get_pond.return_value = self.pond
        self.repository.get_reporter.return_value = self.reporter
        self.repository.get_cycle.return_value = self.active_cycle
        self.repository.get_existing_fish_death.return_value = None
        self.repository.get_latest_fish_death.return_value = self.fish_death
        self.repository.create_fish_death.return_value = self.fish_death

        result = self.service.create_fish_death("pond-1", "cycle-1", 1, schema)
        self.assertEqual(result, self.fish_death)

    @patch('fish_death.services.fish_death_service.PondFishAmount')
    def test_create_fish_death_exceeds_alive(self, mock_model):
        payload = FishDeathCreateSchema(recorded_at=self.today, fish_death_count=60, fish_alive_count=0)
        latest_death = Mock(fish_alive_count=50)

        self.repository.get_pond.return_value = self.pond
        self.repository.get_reporter.return_value = self.reporter
        self.repository.get_cycle.return_value = self.active_cycle
        self.repository.get_existing_fish_death.return_value = None
        self.repository.get_latest_fish_death.return_value = latest_death

        with self.assertRaises(HttpError) as context:
            self.service.create_fish_death("pond-1", "cycle-1", 1, payload)
        self.assertEqual(context.exception.status_code, 400)
        self.assertIn("Jumlah ikan mati melebihi jumlah ikan bertahan", context.exception.message)

    @patch('fish_death.services.fish_death_service.get_supervisor', return_value="owner-1")
    @patch('fish_death.services.fish_death_service.CycleRepo.get_active_cycle')
    def test_list_fish_deaths_success(self, mock_get_cycle, mock_get_supervisor):
        mock_get_cycle.return_value = self.active_cycle
        self.repository.get_pond.return_value = self.pond
        self.repository.list_fish_deaths.return_value = [self.fish_death]

        result = self.service.list_fish_deaths("pond-1", self.user)
        self.assertEqual(result["cycle_id"], self.active_cycle.id)
        self.assertEqual(result["fish_deaths"], [self.fish_death])

    @patch('fish_death.services.fish_death_service.get_supervisor', return_value="owner-1")
    @patch('fish_death.services.fish_death_service.CycleRepo.get_active_cycle', return_value=None)
    def test_list_fish_deaths_cycle_none(self, mock_get_cycle, mock_get_supervisor):
        self.repository.get_pond.return_value = self.pond
        with self.assertRaises(HttpError) as context:
            self.service.list_fish_deaths("pond-1", self.user)
        self.assertEqual(context.exception.status_code, 404)
        self.assertEqual(context.exception.message, "Cycle not active")

    @patch('fish_death.services.fish_death_service.get_supervisor')
    @patch('fish_death.services.fish_death_service.CycleRepo.get_active_cycle')
    def test_list_fish_deaths_pond_not_found(self, mock_get_cycle, mock_get_supervisor):
        mock_get_cycle.return_value = self.active_cycle
        mock_get_supervisor.return_value = self.reporter
        self.repository.get_pond.side_effect = ObjectDoesNotExist

        with self.assertRaises(HttpError) as context:
            self.service.list_fish_deaths("pond-1", self.user)
        self.assertEqual(context.exception.status_code, 404)
        self.assertEqual(context.exception.message, self.service.DATA_NOT_FOUND)

    @patch('fish_death.services.fish_death_service.PondFishAmount.objects.get')
    def test_create_fish_death_existing_deleted(self, mock_get_amount):
        schema = FishDeathCreateSchema(recorded_at=self.today, fish_death_count=10)
        mock_get_amount.return_value.fish_amount = 100
        existing = Mock()

        self.repository.get_pond.return_value = self.pond
        self.repository.get_cycle.return_value = self.active_cycle
        self.repository.get_reporter.return_value = self.reporter
        self.repository.get_existing_fish_death.return_value = existing
        self.repository.get_latest_fish_death.return_value = None
        self.repository.create_fish_death.return_value = self.fish_death

        result = self.service.create_fish_death("pond-1", "cycle-1", 1, schema)
        self.repository.delete_fish_death.assert_called_once_with(existing)
        self.assertEqual(result, self.fish_death)

    @patch('fish_death.services.fish_death_service.PondFishAmount.objects.get')
    def test_create_fish_death_raise_value_error(self, mock_get_amount):
        schema = FishDeathCreateSchema(recorded_at=self.today, fish_death_count=10)
        mock_get_amount.return_value.fish_amount = 100

        self.repository.get_pond.return_value = self.pond
        self.repository.get_cycle.return_value = self.active_cycle
        self.repository.get_reporter.return_value = self.reporter
        self.repository.get_existing_fish_death.return_value = None
        self.repository.get_latest_fish_death.return_value = None
        self.repository.create_fish_death.side_effect = ValueError

        with self.assertRaises(HttpError) as context:
            self.service.create_fish_death("pond-1", "cycle-1", 1, schema)
        self.assertEqual(context.exception.status_code, 400)
        self.assertEqual(context.exception.message, self.service.INVALID_FISH_DEATH_COUNT)

    @patch('fish_death.services.fish_death_service.get_supervisor', return_value=Mock(id=1))
    @patch('fish_death.services.fish_death_service.CycleRepo.get_active_cycle')
    def test_list_fish_deaths_authorize_user_returns_true(self, mock_get_cycle, mock_get_supervisor):
        mock_get_cycle.return_value = self.active_cycle
        self.repository.get_pond.return_value = self.pond

        with patch.object(FishDeathService, "authorize_user", return_value=True):
            with self.assertRaises(HttpError) as context:
                self.service.list_fish_deaths("pond-1", self.user)
        self.assertEqual(context.exception.status_code, 401)
        self.assertEqual(context.exception.message, self.service.UNAUTHORIZED_ACCESS)
