import unittest
import uuid
from unittest.mock import Mock, patch, MagicMock
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
        self.future_date = self.today + timedelta(days=30)
        self.past_date = self.today - timedelta(days=30)

        # Use real UUIDs instead of string identifiers
        self.cycle_id = uuid.uuid4()
        self.pond_id = uuid.uuid4()
        self.fish_death_id = uuid.uuid4()
        self.user_id = uuid.uuid4()
        self.reporter_id = uuid.uuid4()

        self.active_cycle = Mock(spec=Cycle)
        self.active_cycle.id = self.cycle_id
        self.active_cycle.start_date = self.past_date
        self.active_cycle.end_date = self.future_date
        
        self.inactive_cycle = Mock(spec=Cycle)
        self.inactive_cycle.id = uuid.uuid4()
        self.inactive_cycle.start_date = self.past_date
        self.inactive_cycle.end_date = self.past_date  
        
        self.pond = Mock(spec=Pond)
        self.pond.id = self.pond_id
        self.pond.owner = "owner-1"

        self.user = Mock()
        self.user.id = self.user_id
        
        self.reporter = Mock()
        self.reporter.id = self.reporter_id
        
        self.fish_death = Mock(spec=FishDeath)
        self.fish_death.id = self.fish_death_id
        self.fish_death.pond = self.pond
        self.fish_death.cycle = self.active_cycle
        self.fish_death.fish_death_count = 5
        self.fish_death.fish_alive_count = 95
        self.fish_death.recorded_at = self.today

    def test_check_cycle_active_success(self):
        self.service.check_cycle_active(self.active_cycle)

    def test_check_cycle_active_failure(self):
        with self.assertRaises(HttpError) as context:
            self.service.check_cycle_active(self.inactive_cycle)
        
        self.assertEqual(context.exception.status_code, 400)
        self.assertEqual(context.exception.message, self.service.DATA_NOT_FOUND)

    @patch('fish_death.services.fish_death_service.get_supervisor')
    def test_authorize_user_success(self, mock_get_supervisor):
        mock_get_supervisor.return_value = "owner-1"
        self.service.authorize_user(self.user, self.pond)
        mock_get_supervisor.assert_called_once_with(self.user)

    @patch('fish_death.services.fish_death_service.get_supervisor')
    def test_authorize_user_failure(self, mock_get_supervisor):
        mock_get_supervisor.return_value = "other-owner"

        with self.assertRaises(HttpError) as context:
            self.service.authorize_user(self.user, self.pond)
        
        self.assertEqual(context.exception.status_code, 401)
        self.assertEqual(context.exception.message, self.service.UNAUTHORIZED_ACCESS)
        mock_get_supervisor.assert_called_once_with(self.user)

    def test_get_fish_death_success(self):
        self.repository.get_cycle.return_value = self.active_cycle
        self.repository.get_pond.return_value = self.pond
        self.repository.get_fish_death_by_id.return_value = self.fish_death

        with patch('fish_death.services.fish_death_service.get_supervisor', return_value="owner-1"):
            result = self.service.get_fish_death(self.cycle_id, self.pond_id, self.fish_death_id, self.user)
            self.assertEqual(result, self.fish_death)

    def test_get_fish_death_wrong_cycle_or_pond(self):
        wrong_cycle = Mock(spec=Cycle)
        wrong_cycle.id = uuid.uuid4()
        wrong_pond = Mock(spec=Pond)
        wrong_pond.id = uuid.uuid4()
        self.fish_death.cycle = wrong_cycle  # mismatch

        self.repository.get_cycle.return_value = self.active_cycle
        self.repository.get_pond.return_value = self.pond
        self.repository.get_fish_death_by_id.return_value = self.fish_death

        with self.assertRaises(HttpError) as context:
            self.service.get_fish_death(self.cycle_id, self.pond_id, self.fish_death_id, self.user)
        self.assertEqual(context.exception.status_code, 404)

    def test_get_latest_fish_death_not_found(self):
        self.repository.get_cycle.return_value = self.active_cycle
        self.repository.get_pond.return_value = self.pond
        self.repository.get_latest_fish_death.return_value = None

        with patch('fish_death.services.fish_death_service.get_supervisor', return_value="owner-1"):
            with self.assertRaises(HttpError) as context:
                self.service.get_latest_fish_death(self.cycle_id, self.pond_id, self.user)
            self.assertEqual(context.exception.status_code, 404)

    @patch('fish_death.services.fish_death_service.get_supervisor')
    def test_create_fish_death_success(self, mock_get_supervisor):
        mock_get_supervisor.return_value = "owner-1"
        schema = FishDeathCreateSchema(
            recorded_at=self.today,
            fish_death_count=5
        )
        
        # Mock PondFishAmount.objects.get
        mock_pond_fish_amount = MagicMock()
        mock_pond_fish_amount.fish_amount = 100
        
        with patch('fish_death.services.fish_death_service.PondFishAmount.objects.only') as mock_only:
            mock_only.return_value.get.return_value = mock_pond_fish_amount
            
            self.repository.get_latest_fish_death.return_value = self.fish_death
            self.repository.get_existing_fish_death.return_value = None
            self.repository.create_fish_death.return_value = self.fish_death
            
            result = self.service.create_fish_death(self.pond, self.active_cycle, self.reporter, schema)
            self.assertEqual(result, self.fish_death)
    
    @patch('fish_death.services.fish_death_service.PondFishAmount.objects.only')
    def test_create_fish_death_exceeds_alive(self, mock_only):
        payload = FishDeathCreateSchema(
            recorded_at=self.today,
            fish_death_count=60
        )

        latest_death = Mock(spec=FishDeath)
        latest_death.fish_alive_count = 50

        mock_pond_fish_amount = MagicMock()
        mock_pond_fish_amount.fish_amount = 100
        mock_only.return_value.get.return_value = mock_pond_fish_amount

        self.repository.get_latest_fish_death.return_value = latest_death
        self.repository.get_existing_fish_death.return_value = None

        with self.assertRaises(HttpError) as context:
            self.service.create_fish_death(self.pond, self.active_cycle, self.reporter, payload)

        self.assertEqual(context.exception.status_code, 400)
        self.assertIn("Jumlah ikan mati melebihi jumlah ikan bertahan (50 ekor).", context.exception.message)

    @patch('fish_death.services.fish_death_service.get_supervisor')
    @patch('fish_death.services.fish_death_service.CycleRepo.get_active_cycle')
    def test_list_fish_deaths_success(self, mock_get_active_cycle, mock_get_supervisor):
        mock_get_supervisor.return_value = "owner-1"
        mock_get_active_cycle.return_value = self.active_cycle

        self.repository.get_pond.return_value = self.pond
        self.repository.list_fish_deaths.return_value = [self.fish_death]

        result = self.service.list_fish_deaths(self.pond_id, self.user)
        self.assertEqual(result["cycle_id"], self.active_cycle.id)
        self.assertEqual(result["fish_deaths"], [self.fish_death])

    @patch('fish_death.services.fish_death_service.get_supervisor')
    @patch('fish_death.services.fish_death_service.CycleRepo.get_active_cycle')
    def test_list_fish_deaths_cycle_none(self, mock_get_active_cycle, mock_get_supervisor):
        mock_get_supervisor.return_value = "owner-1"
        mock_get_active_cycle.return_value = None
        self.repository.get_pond.return_value = self.pond

        with self.assertRaises(HttpError) as context:
            self.service.list_fish_deaths(self.pond_id, self.user)
        self.assertEqual(context.exception.status_code, 404)
        self.assertEqual(context.exception.message, "Cycle not active")

    @patch('fish_death.services.fish_death_service.get_supervisor')
    @patch('fish_death.services.fish_death_service.CycleRepo.get_active_cycle')
    def test_list_fish_deaths_pond_not_found(self, mock_get_active_cycle, mock_get_supervisor):
        mock_supervisor = Mock()
        mock_supervisor.id = 1
        mock_get_supervisor.return_value = mock_supervisor

        mock_get_active_cycle.return_value = self.active_cycle
        self.repository.get_pond.side_effect = ObjectDoesNotExist

        with self.assertRaises(HttpError) as context:
            self.service.list_fish_deaths(self.pond_id, self.user)

        self.assertEqual(context.exception.status_code, 404)
        self.assertEqual(context.exception.message, self.service.DATA_NOT_FOUND)

    @patch('fish_death.services.fish_death_service.FishDeath.objects')
    @patch('fish_death.services.fish_death_service.PondFishAmount.objects.only')
    def test_create_fish_death_existing_deleted(self, mock_only, mock_fish_death_objects):
        schema = FishDeathCreateSchema(
            recorded_at=self.today,
            fish_death_count=10
        )
        existing_fish_death = Mock()
        existing_fish_death.id = uuid.uuid4()
        existing_fish_death.fish_death_count = 5
        existing_fish_death.fish_alive_count = 95
        
        mock_get = mock_fish_death_objects.get
        mock_get.return_value = self.fish_death
        
        mock_filter = mock_fish_death_objects.filter
        mock_filter.return_value.update.return_value = 1
        
        mock_pond_fish_amount = MagicMock()
        mock_pond_fish_amount.fish_amount = 100
        mock_only.return_value.get.return_value = mock_pond_fish_amount
        
        self.repository.get_existing_fish_death.return_value = existing_fish_death
        self.repository.get_latest_fish_death.return_value = None

        result = self.service.create_fish_death(self.pond, self.active_cycle, self.reporter, schema)
        self.assertEqual(result, self.fish_death)
        mock_fish_death_objects.filter.assert_called_once_with(id=existing_fish_death.id)

    @patch('fish_death.services.fish_death_service.PondFishAmount.objects.only')
    def test_create_fish_death_raise_value_error(self, mock_only):
        schema = FishDeathCreateSchema(
            recorded_at=self.today,
            fish_death_count=10
        )

        mock_pond_fish_amount = MagicMock()
        mock_pond_fish_amount.fish_amount = 100
        mock_only.return_value.get.return_value = mock_pond_fish_amount

        self.repository.get_existing_fish_death.return_value = None
        self.repository.get_latest_fish_death.return_value = None
        self.repository.create_fish_death.side_effect = ValueError

        with self.assertRaises(HttpError) as context:
            self.service.create_fish_death(self.pond, self.active_cycle, self.reporter, schema)

        self.assertEqual(context.exception.status_code, 400)
        self.assertEqual(context.exception.message, self.service.INVALID_FISH_DEATH_COUNT)

    @patch('fish_death.services.fish_death_service.get_supervisor')
    @patch('fish_death.services.fish_death_service.CycleRepo.get_active_cycle')
    def test_list_fish_deaths_authorize_user_returns_true(self, mock_get_active_cycle, mock_get_supervisor):
        mock_supervisor = Mock()
        mock_supervisor.id = 1
        mock_get_supervisor.return_value = mock_supervisor
        mock_get_active_cycle.return_value = self.active_cycle

        self.repository.get_pond.return_value = self.pond

        # Simulasi authorize_user tidak raise error tapi return True
        with patch.object(FishDeathService, "authorize_user", return_value=True):
            with self.assertRaises(HttpError) as context:
                self.service.list_fish_deaths(self.pond_id, self.user)

        self.assertEqual(context.exception.status_code, 401)
        self.assertEqual(context.exception.message, self.service.UNAUTHORIZED_ACCESS)