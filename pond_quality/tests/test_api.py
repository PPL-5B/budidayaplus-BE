from datetime import datetime, timedelta
from unittest.mock import patch
from django.test import TestCase
from django.contrib.auth.models import User
from pond.models import Pond
from cycle.models import Cycle
from pond_quality.models import PondQuality
from ninja_jwt.tokens import AccessToken
from ninja.testing import TestClient
from pond_quality.api import router
import json, uuid
from user_profile.models import UserProfile  

class PondQualityAPITest(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.user = User.objects.create_user(username='081234567890', password='password')
        self.user_profile = UserProfile.objects.create(user=self.user)

        date_now = datetime.now()
        starting_date = date_now - timedelta(days=30)
        ending_date = starting_date + timedelta(days=60)
        self.cycle = Cycle.objects.create(
            supervisor=self.user,
            start_date=starting_date,
            end_date=ending_date
        )

        self.pond = Pond.objects.create(
            owner = self.user,
            name = 'Test Pond',
            image_name = 'test.jpg',
            length = 1.0,
            width = 1.0,
            depth = 1.0
        )
        self.pond2 = Pond.objects.create(
            owner = self.user,
            name = 'Test Pond 2',
            image_name = 'test.jpg',
            length = 1.0,
            width = 1.0,
            depth = 1.0
        )
        self.pond_quality = PondQuality.objects.create(
            pond = self.pond,
            reporter = self.user,
            cycle = self.cycle,
            image_name = 'test.jpg',
            ph_level = 7.0,
            salinity = 0.0,
            water_temperature = 25.0,
            water_clarity = 0.0,
            water_circulation = 0.0,
            dissolved_oxygen = 0.0,
            orp = 0.0,
            ammonia = 0.0,
            nitrate = 0.0,
            phosphate = 0.0
        )

    def test_add_pond_quality_positive(self):
        response = self.client.post(f'/{self.cycle.id}/{self.pond.pond_id}/', data=json.dumps({
            'image_name': 'test.jpg',
            'ph_level': 7.0,
            'salinity': 0.0,
            'water_temperature': 25.0,
            'water_clarity': 0.0,
            'water_circulation': 0.0,
            'dissolved_oxygen': 0.0,
            'orp': 0.0,
            'ammonia': 0.0,
            'nitrate': 0.0,
            'phosphate': 0.0
        }), content_type='application/json', headers={"Authorization": f"Bearer {str(AccessToken.for_user(self.user))}"})
        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['pond'], str(self.pond.pond_id))
        self.assertEqual(data['image_name'], 'test.jpg')
        self.assertEqual(data['ph_level'], 7.0)

    def test_add_pond_quality_already_existing(self):
        response = self.client.post(f'/{self.cycle.id}/{self.pond.pond_id}/', data=json.dumps({
            'image_name': 'test.jpg',
            'ph_level': 7.0,
            'salinity': 0.0,
            'water_temperature': 25.0,
            'water_clarity': 0.0,
            'water_circulation': 0.0,
            'dissolved_oxygen': 0.0,
            'orp': 0.0,
            'ammonia': 0.0,
            'nitrate': 0.0,
            'phosphate': 0.0
        }), content_type='application/json', headers={"Authorization": f"Bearer {str(AccessToken.for_user(self.user))}"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(PondQuality.objects.filter(cycle=self.cycle, pond=self.pond).count(), 1)

    def test_add_pond_quality_no_image_name(self):
        response = self.client.post(f'/{self.cycle.id}/{self.pond.pond_id}/', data=json.dumps({
            'ph_level': 7.0,
            'salinity': 0.0,
            'water_temperature': 25.0,
            'water_clarity': 0.0,
            'water_circulation': 0.0,
            'dissolved_oxygen': 0.0,
            'orp': 0.0,
            'ammonia': 0.0,
            'nitrate': 0.0,
            'phosphate': 0.0
        }), content_type='application/json', headers={"Authorization": f"Bearer {str(AccessToken.for_user(self.user))}"})
        self.assertEqual(response.status_code, 200)

    def test_add_pond_quality_invalid_pond(self):
        response = self.client.post(f'/{self.cycle.id}/{uuid.uuid4()}/', data=json.dumps({
            'image_name': 'test.jpg',
            'ph_level': 7.0,
            'salinity': 0.0,
            'water_temperature': 25.0,
            'water_clarity': 0.0,
            'water_circulation': 0.0,
            'dissolved_oxygen': 0.0,
            'orp': 0.0,
            'ammonia': 0.0,
            'nitrate': 0.0,
            'phosphate': 0.0
        }), content_type='application/json', headers={"Authorization": f"Bearer {str(AccessToken.for_user(self.user))}"})
        self.assertEqual(response.status_code, 404)

    def test_add_pond_quality_invalid_token(self):
        response = self.client.post(f'/{self.cycle.id}/{self.pond.pond_id}/', data=json.dumps({
            'image_name': 'test.jpg',
            'ph_level': 7.0,
            'salinity': 0.0,
            'water_temperature': 25.0,
            'water_clarity': 0.0,
            'water_circulation': 0.0,
            'dissolved_oxygen': 0.0,
            'orp': 0.0,
            'ammonia': 0.0,
            'nitrate': 0.0,
            'phosphate': 0.0
        }), content_type='application/json', headers={"Authorization": "Bearer Invalid Token"})
        self.assertEqual(response.status_code, 401)

    def test_add_pond_quality_no_ph_level(self):
        response = self.client.post(f'/{self.cycle.id}/{self.pond.pond_id}/', data=json.dumps({
            'image_name': 'test.jpg',
            'salinity': 0.0,
            'water_temperature': 25.0,
            'water_clarity': 0.0,
            'water_circulation': 0.0,
            'dissolved_oxygen': 0.0,
            'orp': 0.0,
            'ammonia': 0.0,
            'nitrate': 0.0,
            'phosphate': 0.0
        }), content_type='application/json', headers={"Authorization": f"Bearer {str(AccessToken.for_user(self.user))}"})
        self.assertEqual(response.status_code, 422)

    def test_add_pond_quality_no_salinity(self):
        response = self.client.post(f'/{self.cycle.id}/{self.pond.pond_id}/', data=json.dumps({
            'image_name': 'test.jpg',
            'ph_level': 7.0,
            'water_temperature': 25.0,
            'water_clarity': 0.0,
            'water_circulation': 0.0,
            'dissolved_oxygen': 0.0,
            'orp': 0.0,
            'ammonia': 0.0,
            'nitrate': 0.0,
            'phosphate': 0.0
        }), content_type='application/json', headers={"Authorization": f"Bearer {str(AccessToken.for_user(self.user))}"})
        self.assertEqual(response.status_code, 422)

    def test_add_pond_quality_invalid_cycle(self):
        response = self.client.post(f'{uuid.uuid4()}/{self.pond.pond_id}/', data=json.dumps({
            'image_name': 'test.jpg',
            'ph_level': 7.0,
            'salinity': 0.0,
            'water_temperature': 25.0,
            'water_clarity': 0.0,
            'water_circulation': 0.0,
            'dissolved_oxygen': 0.0,
            'orp': 0.0,
            'ammonia': 0.0,
            'nitrate': 0.0,
            'phosphate': 0.0
        }), content_type='application/json', headers={"Authorization": f"Bearer {str(AccessToken.for_user(self.user))}"})
        self.assertEqual(response.status_code, 404)
    
    def test_add_pond_quality_outdated_cycle(self):
        starting_date = datetime.now() - timedelta(days=90)
        ending_date = starting_date + timedelta(days=60)
        cycle = Cycle.objects.create(
            supervisor=self.user,
            start_date=starting_date,
            end_date=ending_date
        )
        response = self.client.post(f'/{cycle.id}/{self.pond.pond_id}/', data=json.dumps({
            'image_name': 'test.jpg',
            'ph_level': 7.0,
            'salinity': 0.0,
            'water_temperature': 25.0,
            'water_clarity': 0.0,
            'water_circulation': 0.0,
            'dissolved_oxygen': 0.0,
            'orp': 0.0,
            'ammonia': 0.0,
            'nitrate': 0.0,
            'phosphate': 0.0
        }), content_type='application/json', headers={"Authorization": f"Bearer {str(AccessToken.for_user(self.user))}"})
        self.assertEqual(response.status_code, 400)

    def test_get_pond_quality_positive(self):
        response = self.client.get(f'/{self.cycle.id}/{self.pond.pond_id}/{self.pond_quality.id}/', headers={"Authorization": f"Bearer {str(AccessToken.for_user(self.user))}"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['ph_level'], 7.0)

    def test_get_pond_quality_invalid_pond(self):
        response = self.client.get(f'/{self.cycle.id}/{uuid.uuid4()}/{self.pond_quality.id}/', headers={"Authorization": f"Bearer {str(AccessToken.for_user(self.user))}"})
        self.assertEqual(response.status_code, 404)

    def test_get_pond_quality_invalid_pond_quality(self):
        response = self.client.get(f'/{self.cycle.id}/{self.pond.pond_id}/{uuid.uuid4()}/', headers={"Authorization": f"Bearer {str(AccessToken.for_user(self.user))}"})
        self.assertEqual(response.status_code, 404)

    def test_get_pond_quality_invalid_token(self):
        response = self.client.get(f'/{self.cycle.id}/{self.pond.pond_id}/{self.pond_quality.id}/', headers={"Authorization": "Bearer Invalid Token"})
        self.assertEqual(response.status_code, 401)


    def test_get_pond_quality_different_pond(self):
        response = self.client.get(f'/{self.cycle.id}/{self.pond2.pond_id}/{self.pond_quality.id}/', headers={"Authorization": f"Bearer {str(AccessToken.for_user(self.user))}"})
        self.assertEqual(response.status_code, 404)

    def test_get_pond_quality_cycle_not_active(self):
        starting_date = datetime.now() - timedelta(days=90)
        ending_date = starting_date + timedelta(days=60)
        cycle = Cycle.objects.create(
            supervisor=self.user,
            start_date=starting_date,
            end_date=ending_date
        )
        response = self.client.get(f'/{cycle.id}/{self.pond.pond_id}/{self.pond_quality.id}/', headers={"Authorization": f"Bearer {str(AccessToken.for_user(self.user))}"})
        self.assertEqual(response.status_code, 400)
    
    def test_get_pond_quality_different_cycle(self):
        starting_date = datetime.now()
        ending_date = starting_date + timedelta(days=60)
        cycle = Cycle.objects.create(
            supervisor=self.user,
            start_date=starting_date,
            end_date=ending_date
            )
        response = self.client.get(f'/{cycle.id}/{self.pond.pond_id}/{self.pond_quality.id}/', headers={"Authorization": f"Bearer {str(AccessToken.for_user(self.user))}"})
        self.assertEqual(response.status_code, 404)

    def test_get_latest_pond_quality_positive(self):
        response = self.client.get(f'/{self.cycle.id}/{self.pond.pond_id}/latest', headers={"Authorization": f"Bearer {str(AccessToken.for_user(self.user))}"})
        self.assertEqual(response.status_code, 200)

    def test_get_latest_pond_quality_invalid_pond(self):
        response = self.client.get(f'/{self.cycle.id}/{uuid.uuid4()}/latest', headers={"Authorization": f"Bearer {str(AccessToken.for_user(self.user))}"})
        self.assertEqual(response.status_code, 404)

    def test_get_latest_pond_quality_invalid_token(self):
        response = self.client.get(f'/{self.cycle.id}/{self.pond.pond_id}/latest', headers={"Authorization": "Bearer Invalid Token"})
        self.assertEqual(response.status_code, 401)
    
    def test_get_latest_pond_quality_not_found(self):
        response = self.client.get(f'/{self.cycle.id}/{self.pond2.pond_id}/latest', headers={"Authorization": f"Bearer {str(AccessToken.for_user(self.user))}"})
        self.assertEqual(response.status_code, 404)
    
    def test_get_latest_pond_quality_cycle_not_active(self):
        starting_date = datetime.now() - timedelta(days=90)
        ending_date = starting_date + timedelta(days=60)
        cycle = Cycle.objects.create(
            supervisor=self.user,
            start_date=starting_date,
            end_date=ending_date
        )
        response = self.client.get(f'/{cycle.id}/{self.pond.pond_id}/latest', headers={"Authorization": f"Bearer {str(AccessToken.for_user(self.user))}"})
        self.assertEqual(response.status_code, 400)

    def test_get_pond_quality_alerts_no_data(self):
        # Jika tidak ada data, API akan mengembalikan response 200 dan pesan "Data belum tersedia"
        PondQuality.objects.all().delete()  # Kosongkan database sebelum tes

        response = self.client.get(
            f'/{self.pond.pond_id}/alerts',
            headers={"Authorization": f"Bearer {str(AccessToken.for_user(self.user))}"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])  # Tidak ada data, maka response kosong


    def test_get_pond_quality_alerts_all_parameters_meet_target(self):
        # Jika semua parameter dalam PondQualitySummary memenuhi target, API harus mengembalikan list kosong []
        PondQuality.objects.all().delete()  # Hapus semua data lama

        # Buat data PondQuality yang sesuai target
        PondQuality.objects.create(
            pond=self.pond,
            reporter=self.user,
            cycle=self.cycle,
            image_name='test.jpg',
            ph_level=8.0,
            salinity=30.0,
            water_temperature=27.0,
            water_clarity=0.0
        )

        response = self.client.get(
            f'/{self.pond.pond_id}/alerts',
            headers={"Authorization": f"Bearer {str(AccessToken.for_user(self.user))}"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])  # Tidak ada alert jika semua parameter sesuai target


    def test_get_pond_quality_alerts_some_parameters_below_target(self):
        # Jika ada parameter yang tidak memenuhi target, peringatan akan muncul
        PondQuality.objects.all().delete()  
        PondQuality.objects.create(
            pond=self.pond,
            reporter=self.user,
            cycle=self.cycle,
            ph_level=6.5,  # Di bawah target (6.5 < 7.5)
            salinity=25.0,  # Di bawah target (25.0 < 30.0)
            water_temperature=27.0,  # Sesuai target
            water_clarity=5.0,  # Di atas target (5.0 > 0)
        )

        response = self.client.get(
            f'/{self.pond.pond_id}/alerts',
            headers={"Authorization": f"Bearer {str(AccessToken.for_user(self.user))}"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(response.json()), 0)  # Harus ada alert
        alerts = response.json()

        expected_alerts = [
            {"parameter": "ph_level", "actual_value": 6.5, "target_value": 7.5, "status": "Below Target"},
            {"parameter": "salinity", "actual_value": 25.0, "target_value": 30.0, "status": "Below Target"},
        ]

        for expected_alert in expected_alerts:
            self.assertIn(expected_alert, alerts)


    def test_get_pond_quality_alerts_invalid_token(self):
        # Token invalid --> harusnya muncul unauthorized
        response = self.client.get(
            f'/{self.pond.pond_id}/alerts',
            headers={"Authorization": "Bearer Invalid Token"}
        )
        self.assertEqual(response.status_code, 401)  # Unauthorized jika token salah


    def test_get_dashboard_table_data_positive(self):
        with patch('pond_quality.api.get_supervisor', return_value=self.user):
            response = self.client.get(f'/{self.cycle.id}/{self.pond.pond_id}/dashboard-table', headers={"Authorization": f"Bearer {str(AccessToken.for_user(self.user))}"})
            self.assertEqual(response.status_code, 200)
            data = response.json()
            
            self.assertIn('recorded_at', data)
            self.assertIn('ph_level', data)
            self.assertIn('salinity', data)
            self.assertIn('water_temperature', data)
            self.assertIn('water_clarity', data)
            
            self.assertEqual(data['ph_level'], 7.0)
            self.assertEqual(data['salinity'], 0.0)
            self.assertEqual(data['water_temperature'], 25.0)
            self.assertEqual(data['water_clarity'], 0.0)
            
            self.assertNotIn('water_circulation', data)
            self.assertNotIn('dissolved_oxygen', data)
            self.assertNotIn('orp', data)
            self.assertNotIn('ammonia', data)
            self.assertNotIn('nitrate', data)
            self.assertNotIn('phosphate', data)

    def test_get_dashboard_table_data_invalid_pond(self):
        with patch('pond_quality.api.get_supervisor', return_value=self.user):
            response = self.client.get(f'/{self.cycle.id}/{uuid.uuid4()}/dashboard-table', headers={"Authorization": f"Bearer {str(AccessToken.for_user(self.user))}"})
            self.assertEqual(response.status_code, 404)

    def test_get_dashboard_table_data_invalid_token(self):
        with patch('pond_quality.api.get_supervisor', return_value=self.user):
            response = self.client.get(f'/{self.cycle.id}/{self.pond.pond_id}/dashboard-table', headers={"Authorization": "Bearer Invalid Token"})
            self.assertEqual(response.status_code, 401)

    def test_get_dashboard_table_data_not_found(self):
        with patch('pond_quality.api.get_supervisor', return_value=self.user):
            response = self.client.get(f'/{self.cycle.id}/{self.pond2.pond_id}/dashboard-table', headers={"Authorization": f"Bearer {str(AccessToken.for_user(self.user))}"})
            self.assertEqual(response.status_code, 404)

    def test_get_dashboard_table_data_cycle_not_active(self):
        with patch('pond_quality.api.get_supervisor', return_value=self.user):
            starting_date = datetime.now() - timedelta(days=90)
            ending_date = starting_date + timedelta(days=60)
            cycle = Cycle.objects.create(
                supervisor=self.user,
                start_date=starting_date,
                end_date=ending_date
            )
            response = self.client.get(f'/{cycle.id}/{self.pond.pond_id}/dashboard-table', headers={"Authorization": f"Bearer {str(AccessToken.for_user(self.user))}"})
            self.assertEqual(response.status_code, 400)

   
