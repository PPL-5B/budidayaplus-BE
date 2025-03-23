from unittest import mock
from unittest.mock import patch, MagicMock
from django.test import TestCase
from datetime import datetime, timedelta
from food_sampling.services.food_sampling_service import FoodSamplingService
from food_sampling.schemas import FoodSamplingCreateSchema
from ninja.errors import HttpError
from pond_quality.api import CYCLE_NOT_ACTIVE

class FoodSamplingServiceTest(TestCase):
    
    @patch('food_sampling.repositories.food_sampling_repository.FoodSamplingRepository')
    def setUp(self, mock_repository):
        self.mock_repository = mock_repository()
        self.service = FoodSamplingService(repository=self.mock_repository)
        
        self.mock_pond = MagicMock()
        self.mock_cycle = MagicMock()
        self.mock_reporter = MagicMock()
        self.mock_food_sampling = MagicMock()
        self.mock_user = MagicMock() 

        self.mock_cycle.start_date = datetime.now().date() - timedelta(days=30)
        self.mock_cycle.end_date = datetime.now().date() + timedelta(days=30)

        self.mock_repository.get_pond.return_value = self.mock_pond
        self.mock_repository.get_cycle.return_value = self.mock_cycle
        self.mock_repository.get_reporter.return_value = self.mock_reporter

    def test_create_food_sampling_existing_entry(self):
        payload = FoodSamplingCreateSchema(
            food_quantity=20,
            recorded_at=datetime.now()
        )
        self.mock_repository.get_existing_food_sampling.return_value = self.mock_food_sampling
        self.mock_repository.create_food_sampling.return_value = self.mock_food_sampling

        result = self.service.create_food_sampling(
            pond_id='test_pond_id',
            cycle_id='test_cycle_id',
            reporter_id=1,
            payload=payload
        )
    
        self.mock_repository.delete_food_sampling.assert_called_once_with(self.mock_food_sampling)
        self.mock_repository.create_food_sampling.assert_called_once()
        self.assertEqual(result, self.mock_food_sampling)

    def test_create_food_sampling_invalid_quantity(self):
        payload = FoodSamplingCreateSchema(
            food_quantity=-10, 
            recorded_at=datetime.now()
        )
        self.mock_repository.get_existing_food_sampling.return_value = None
        self.mock_repository.create_food_sampling.side_effect = ValueError("Invalid food quantity")

        with self.assertRaises(HttpError) as context:
            self.service.create_food_sampling(
                pond_id='test_pond_id',
                cycle_id='test_cycle_id',
                reporter_id=1,
                payload=payload
            )
        
        self.assertEqual(context.exception.status_code, 400)
        self.assertEqual(str(context.exception), self.service.INVALID_FOOD_QUANTITY)

    def test_get_food_sampling(self):
        self.mock_repository.get_food_sampling_by_id.return_value = self.mock_food_sampling
        self.mock_food_sampling.cycle = self.mock_cycle
        self.mock_food_sampling.pond = self.mock_pond
        self.mock_food_sampling.reporter = self.mock_user
        self.mock_pond.owner = self.mock_user
        
        result = self.service.get_food_sampling('cycle_id', 'pond_id', 'sampling_id', self.mock_user)

        self.mock_repository.get_cycle.assert_called_once_with('cycle_id')
        self.mock_repository.get_pond.assert_called_once_with('pond_id')
        self.mock_repository.get_food_sampling_by_id.assert_called_once_with('sampling_id')
        self.assertEqual(result, self.mock_food_sampling)

    def test_get_food_sampling_unauthorized_access(self):
        self.mock_repository.get_food_sampling_by_id.return_value = self.mock_food_sampling
        self.mock_food_sampling.cycle = self.mock_cycle
        self.mock_food_sampling.pond = self.mock_pond
        self.mock_food_sampling.reporter = MagicMock()  
        self.mock_pond.owner = MagicMock()  

        with self.assertRaises(HttpError) as context:
            self.service.get_food_sampling('cycle_id', 'pond_id', 'sampling_id', self.mock_user)
        
        self.assertEqual(context.exception.status_code, 401)

    def test_get_latest_food_sampling(self):
        self.mock_repository.get_latest_food_sampling.return_value = self.mock_food_sampling
        self.mock_food_sampling.reporter = self.mock_user
        self.mock_pond.owner = self.mock_user

        result = self.service.get_latest_food_sampling('cycle_id', 'pond_id', self.mock_user)
        
        self.mock_repository.get_cycle.assert_called_once_with('cycle_id')
        self.mock_repository.get_pond.assert_called_once_with('pond_id')
        self.mock_repository.get_latest_food_sampling.assert_called_once_with(self.mock_pond, self.mock_cycle)
        self.assertEqual(result, self.mock_food_sampling)

    def test_get_latest_food_sampling_not_found(self):
        self.mock_repository.get_latest_food_sampling.return_value = None

        with self.assertRaises(HttpError) as context:
            self.service.get_latest_food_sampling('cycle_id', 'pond_id', self.mock_user)

        self.assertEqual(context.exception.status_code, 404)

    @patch('user_profile.utils.get_supervisor')
    @patch('cycle.repositories.cycle_repo.CycleRepo.get_active_cycle') 
    def test_list_food_samplings(self, mock_get_active_cycle, mock_get_supervisor):
        self.mock_repository.list_food_samplings.return_value = [self.mock_food_sampling]
        self.mock_cycle.supervisor = self.mock_user
        
        with patch('food_sampling.services.food_sampling_service.CycleRepo.get_active_cycle') as mock_get_active_cycle:
            mock_get_active_cycle.return_value = self.mock_cycle
        
            with patch('food_sampling.services.food_sampling_service.get_supervisor') as mock_get_supervisor:
                mock_get_supervisor.return_value = self.mock_user
                
                self.service.authorize_user = MagicMock(return_value=False)
                
                result = self.service.list_food_samplings('pond_id', self.mock_user)
                
                mock_get_active_cycle.assert_called_once_with(self.mock_user)
                
                self.mock_repository.get_pond.assert_called_once_with('pond_id')
                self.mock_repository.list_food_samplings.assert_called_once_with(self.mock_cycle, self.mock_pond)

                expected_result = {
                    'food_samplings': [self.mock_food_sampling],
                    'cycle_id': self.mock_cycle.id
                }
                self.assertEqual(result, expected_result)

    def test_list_food_samplings_unauthorized_access(self):
        self.mock_cycle.start_date = datetime.now().date() - timedelta(days=30)
        self.mock_cycle.end_date = datetime.now().date() + timedelta(days=30)
        self.mock_cycle.supervisor = MagicMock()

        with patch('food_sampling.services.food_sampling_service.CycleRepo.get_active_cycle') as mock_get_active_cycle:
            mock_get_active_cycle.return_value = self.mock_cycle
            
            with patch('food_sampling.services.food_sampling_service.get_supervisor') as mock_get_supervisor:
                mock_get_supervisor.return_value = self.mock_user
                
                self.service.authorize_user = MagicMock(return_value=True)
                
                with self.assertRaises(HttpError) as context:
                    self.service.list_food_samplings('pond_id', self.mock_user)
                    
                self.assertEqual(context.exception.status_code, 401)
    
    def test_list_food_samplings_no_active_cycle(self):
        with patch('food_sampling.services.food_sampling_service.CycleRepo.get_active_cycle') as mock_get_active_cycle:
            mock_get_active_cycle.return_value = None
            
            with patch('food_sampling.services.food_sampling_service.get_supervisor') as mock_get_supervisor:
                mock_get_supervisor.return_value = self.mock_user
                self.service.authorize_user = MagicMock(return_value=False)

                with self.assertRaises(HttpError) as context:
                    self.service.list_food_samplings('pond_id', self.mock_user)
                
                self.assertEqual(context.exception.status_code, 404)
                self.assertEqual(context.exception.message, CYCLE_NOT_ACTIVE)

    def test_create_food_sampling_success(self, mocker):
        mocker.patch.object(self.repository, "get_pond", return_value=self.mock_pond)
        mocker.patch.object(self.repository, "get_reporter", return_value=self.mock_user)
        mocker.patch.object(self.repository, "get_cycle", return_value=self.mock_cycle)

        response = self.service.create_food_sampling("pond-123", "cycle-456", 2, self.payload_valid)

        assert response is not None
        assert response.food_quantity == self.payload_valid.food_quantity
        assert response.recorded_at == self.payload_valid.recorded_at

    def test_create_food_sampling_exceed_threshold(self):
        service = FoodSamplingService(repository=MagicMock())

        with self.assertRaises(HttpError) as excinfo:
            service.create_food_sampling("pond-123", "cycle-456", 2, FoodSamplingCreateSchema(food_quantity=1200, recorded_at=datetime.now()))

        self.assertEqual(excinfo.exception.status_code, 400)
        self.assertEqual(str(excinfo.exception), "Gagal menyimpan sample makanan")