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

class TestFishDeathService(unittest.TestCase):
    def setUp(self):
        self.repository = Mock(spec=FishDeathRepository)
        self.service = FishDeathService(self.repository)
        self.today = datetime.now().date()
        self.future_date = self.today + timedelta(days=30)
        self.past_date = self.today - timedelta(days=30)

        self.active_cycle = Mock(spec=Cycle)
        self.active_cycle.id = "cycle-1"
        self.active_cycle.start_date = self.past_date
        self.active_cycle.end_date = self.future_date
        
        self.inactive_cycle = Mock(spec=Cycle)
        self.inactive_cycle.id = "cycle-2"
        self.inactive_cycle.start_date = self.past_date
        self.inactive_cycle.end_date = self.past_date  
        
        self.pond = Mock(spec=Pond)
        self.pond.id = "pond-1"
        self.pond.owner = "owner-1"

        self.user = Mock()
        self.user.id = "user-1"
        
        self.reporter = Mock()
        self.reporter.id = 1
        
        self.fish_death = Mock(spec=FishDeath)
        self.fish_death.id = "fish-death-1"
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

    @patch('fish_death.services.fish_death_service.get_supervisor')
    def test_get_fish_death_success(self, mock_get_supervisor):
        mock_get_supervisor.return_value = "owner-1"
        self.repository.get_cycle.return_value = self.active_cycle
        self.repository.get_pond.return_value = self.pond
        self.repository.get_fish_death_by_id.return_value = self.fish_death
        result = self.service.get_fish_death("cycle-1", "pond-1", "fish-death-1", self.user)
        self.assertEqual(result, self.fish_death)
        self.assertEqual(result.target_fish_death_count, 1)  
        self.repository.get_cycle.assert_called_once_with("cycle-1")
        self.repository.get_pond.assert_called_once_with("pond-1")
        self.repository.get_fish_death_by_id.assert_called_once_with("fish-death-1")
        mock_get_supervisor.assert_called_once_with(self.user)

    @patch('fish_death.services.fish_death_service.get_supervisor')
    def test_get_fish_death_inactive_cycle(self, mock_get_supervisor):
        mock_get_supervisor.return_value = "owner-1"
        self.repository.get_cycle.return_value = self.inactive_cycle
        self.repository.get_pond.return_value = self.pond
        
        with self.assertRaises(HttpError) as context:
            self.service.get_fish_death("cycle-2", "pond-1", "fish-death-1", self.user)
        
        self.assertEqual(context.exception.status_code, 400)
        self.assertEqual(context.exception.message, self.service.DATA_NOT_FOUND)

    @patch('fish_death.services.fish_death_service.get_supervisor')
    def test_get_fish_death_wrong_association(self, mock_get_supervisor):
        mock_get_supervisor.return_value = "owner-1"
        different_cycle = Mock(spec=Cycle)
        different_cycle.id = "cycle-3"
        different_cycle.start_date = self.past_date
        different_cycle.end_date = self.future_date
        self.fish_death.cycle = different_cycle  
        self.repository.get_cycle.return_value = self.active_cycle
        self.repository.get_pond.return_value = self.pond
        self.repository.get_fish_death_by_id.return_value = self.fish_death
        
        with self.assertRaises(HttpError) as context:
            self.service.get_fish_death("cycle-1", "pond-1", "fish-death-1", self.user)
        
        self.assertEqual(context.exception.status_code, 404)
        self.assertEqual(context.exception.message, self.service.DATA_NOT_FOUND)

    @patch('fish_death.services.fish_death_service.get_supervisor')
    def test_get_fish_death_unauthorized(self, mock_get_supervisor):
        mock_get_supervisor.return_value = "other-owner"
        self.repository.get_cycle.return_value = self.active_cycle
        self.repository.get_pond.return_value = self.pond
        self.repository.get_fish_death_by_id.return_value = self.fish_death
        
        with self.assertRaises(HttpError) as context:
            self.service.get_fish_death("cycle-1", "pond-1", "fish-death-1", self.user)
        
        self.assertEqual(context.exception.status_code, 401)
        self.assertEqual(context.exception.message, self.service.UNAUTHORIZED_ACCESS)

    @patch('fish_death.services.fish_death_service.get_supervisor')
    def test_get_latest_fish_death_success(self, mock_get_supervisor):
        mock_get_supervisor.return_value = "owner-1"
        self.repository.get_cycle.return_value = self.active_cycle
        self.repository.get_pond.return_value = self.pond
        self.repository.get_latest_fish_death.return_value = self.fish_death
        result = self.service.get_latest_fish_death("cycle-1", "pond-1", self.user)
        self.assertEqual(result, self.fish_death)
        self.assertEqual(result.target_fish_death_count, 1)  
        self.repository.get_cycle.assert_called_once_with("cycle-1")
        self.repository.get_pond.assert_called_once_with("pond-1")
        self.repository.get_latest_fish_death.assert_called_once_with(self.pond, self.active_cycle)
        mock_get_supervisor.assert_called_once_with(self.user)

    @patch('fish_death.services.fish_death_service.get_supervisor')
    def test_get_latest_fish_death_not_found(self, mock_get_supervisor):
        mock_get_supervisor.return_value = "owner-1"
        self.repository.get_cycle.return_value = self.active_cycle
        self.repository.get_pond.return_value = self.pond
        self.repository.get_latest_fish_death.return_value = None

        with self.assertRaises(HttpError) as context:
            self.service.get_latest_fish_death("cycle-1", "pond-1", self.user)
        
        self.assertEqual(context.exception.status_code, 404)
        self.assertEqual(context.exception.message, self.service.DATA_NOT_FOUND)

    @patch('fish_death.services.fish_death_service.get_supervisor')
    def test_get_latest_fish_death_unauthorized(self, mock_get_supervisor):
        mock_get_supervisor.return_value = "other-owner"
        self.repository.get_cycle.return_value = self.active_cycle
        self.repository.get_pond.return_value = self.pond
        self.repository.get_latest_fish_death.return_value = self.fish_death
        
        with self.assertRaises(HttpError) as context:
            self.service.get_latest_fish_death("cycle-1", "pond-1", self.user)
        
        self.assertEqual(context.exception.status_code, 401)
        self.assertEqual(context.exception.message, self.service.UNAUTHORIZED_ACCESS)

    @patch('fish_death.services.fish_death_service.get_supervisor')
    @patch('fish_death.services.fish_death_service.CycleRepo.get_active_cycle')
    def test_list_fish_deaths_success(self, mock_get_active_cycle, mock_get_supervisor):
        mock_get_supervisor.return_value = "owner-1"
        mock_get_active_cycle.return_value = self.active_cycle
        self.repository.get_pond.return_value = self.pond
        self.repository.list_fish_deaths.return_value = [self.fish_death]
        self.service.authorize_user = Mock(return_value=False)
        result = self.service.list_fish_deaths("pond-1", self.user)
        self.assertEqual(result["fish_deaths"], [self.fish_death])
        self.assertEqual(result["cycle_id"], "cycle-1")
        self.assertEqual(self.fish_death.target_fish_death_count, 1)
        self.repository.get_pond.assert_called_once_with("pond-1")
        self.repository.list_fish_deaths.assert_called_once_with(self.active_cycle, self.pond)
        self.service.authorize_user.assert_called_once_with(self.user, self.pond)
        mock_get_supervisor.assert_called_once_with(self.user)
        mock_get_active_cycle.assert_called_once_with("owner-1")

    @patch('fish_death.services.fish_death_service.get_supervisor')
    @patch('fish_death.services.fish_death_service.CycleRepo.get_active_cycle')
    def test_list_fish_deaths_pond_not_found(self, mock_get_active_cycle, mock_get_supervisor):
        mock_get_supervisor.return_value = "owner-1"
        mock_get_active_cycle.return_value = self.active_cycle
        self.repository.get_pond.side_effect = Exception("Pond not found")
        
        with self.assertRaises(HttpError) as context:
            self.service.list_fish_deaths("pond-1", self.user)
        
        self.assertEqual(context.exception.status_code, 404)
        self.assertEqual(context.exception.message, self.service.DATA_NOT_FOUND)

    @patch('fish_death.services.fish_death_service.get_supervisor')
    @patch('fish_death.services.fish_death_service.CycleRepo.get_active_cycle')
    def test_list_fish_deaths_unauthorized(self, mock_get_active_cycle, mock_get_supervisor):
        mock_get_supervisor.return_value = "owner-1"
        mock_get_active_cycle.return_value = self.active_cycle
        self.repository.get_pond.return_value = self.pond
        self.service.authorize_user = Mock(return_value=True)
        
        with self.assertRaises(HttpError) as context:
            self.service.list_fish_deaths("pond-1", self.user)
        
        self.assertEqual(context.exception.status_code, 401)
        self.assertEqual(context.exception.message, self.service.UNAUTHORIZED_ACCESS)

    @patch('fish_death.services.fish_death_service.get_supervisor')
    @patch('fish_death.services.fish_death_service.CycleRepo.get_active_cycle')
    def test_list_fish_deaths_cycle_not_active(self, mock_get_active_cycle, mock_get_supervisor):
        mock_get_supervisor.return_value = "owner-1"
        mock_get_active_cycle.return_value = None
        self.repository.get_pond.return_value = self.pond
        self.service.authorize_user = Mock(return_value=False)
        
        with self.assertRaises(HttpError) as context:
            self.service.list_fish_deaths("pond-1", self.user)
        
        self.assertEqual(context.exception.status_code, 404)
        self.assertEqual(context.exception.message, "Cycle not active")

    def test_create_fish_death_success(self):
        payload = FishDeathCreateSchema(
            recorded_at=self.today,
            fish_death_count=5,
            fish_alive_count=95
        )
        
        self.repository.get_pond.return_value = self.pond
        self.repository.get_reporter.return_value = self.reporter
        self.repository.get_cycle.return_value = self.active_cycle
        self.repository.get_existing_fish_death.return_value = None
        self.repository.create_fish_death.return_value = self.fish_death
        result = self.service.create_fish_death("pond-1", "cycle-1", 1, payload)
        self.assertEqual(result, self.fish_death)
        self.assertEqual(result.target_fish_death_count, 1)
        self.repository.get_pond.assert_called_once_with("pond-1")
        self.repository.get_reporter.assert_called_once_with(1)
        self.repository.get_cycle.assert_called_once_with("cycle-1")
        self.repository.get_existing_fish_death.assert_called_once_with(self.active_cycle, self.pond, self.today)
        self.repository.create_fish_death.assert_called_once_with(
            pond=self.pond,
            reporter=self.reporter,
            cycle=self.active_cycle,
            recorded_at=payload.recorded_at,
            fish_death_count=payload.fish_death_count,
            fish_alive_count=payload.fish_alive_count
        )

    def test_create_fish_death_existing_record(self):
        payload = FishDeathCreateSchema(
            recorded_at=self.today,
            fish_death_count=5,
            fish_alive_count=95
        )
        existing_fish_death = Mock(spec=FishDeath)
        existing_fish_death.id = "existing-fish-death"
        self.repository.get_pond.return_value = self.pond
        self.repository.get_reporter.return_value = self.reporter
        self.repository.get_cycle.return_value = self.active_cycle
        self.repository.get_existing_fish_death.return_value = existing_fish_death
        self.repository.create_fish_death.return_value = self.fish_death
        result = self.service.create_fish_death("pond-1", "cycle-1", 1, payload)
        self.assertEqual(result, self.fish_death)
        self.repository.delete_fish_death.assert_called_once_with(existing_fish_death)
        self.repository.create_fish_death.assert_called_once()

    def test_create_fish_death_invalid_count(self):
        payload = FishDeathCreateSchema(
            recorded_at=self.today,
            fish_death_count=5,
            fish_alive_count=95
        )
        
        self.repository.get_pond.return_value = self.pond
        self.repository.get_reporter.return_value = self.reporter
        self.repository.get_cycle.return_value = self.active_cycle
        self.repository.get_existing_fish_death.return_value = None
        self.repository.create_fish_death.side_effect = ValueError("Invalid fish death count")
        
        with self.assertRaises(HttpError) as context:
            self.service.create_fish_death("pond-1", "cycle-1", 1, payload)
        
        self.assertEqual(context.exception.status_code, 400)
        self.assertEqual(context.exception.message, self.service.INVALID_FISH_DEATH_COUNT)

    def test_target_fish_death_count_edge_cases(self):
        self.repository.get_cycle.return_value = self.active_cycle
        self.repository.get_pond.return_value = self.pond
        self.repository.list_fish_deaths.return_value = [self.fish_death] * 101  
        self.service.authorize_user = Mock(return_value=False)
        
        with patch('fish_death.services.fish_death_service.CycleRepo.get_active_cycle') as mock_get_active_cycle:
            mock_get_active_cycle.return_value = self.active_cycle
            
            with patch('fish_death.services.fish_death_service.get_supervisor') as mock_get_supervisor:
                mock_get_supervisor.return_value = "owner-1"                
                result = self.service.list_fish_deaths("pond-1", self.user)
                self.assertEqual(result["fish_deaths"][100].target_fish_death_count, 1)                
                self.assertEqual(result["fish_deaths"][99].target_fish_death_count, 100)                
                self.assertEqual(result["fish_deaths"][0].target_fish_death_count, 1)