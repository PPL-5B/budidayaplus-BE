import uuid
from django.test import TestCase
from django.contrib.auth.models import User
from ninja.testing import TestClient
from fish_sampling.models import Pond, FishSampling, Cycle
from fish_sampling.api import router
import json
from rest_framework_simplejwt.tokens import AccessToken
from datetime import datetime, timedelta
from django.utils.timezone import make_aware
from user_profile.models import UserProfile, Worker
from fish_sampling.api import determine_fish_status, target_data

class FishSamplingAPITest(TestCase):
    def setUp(self):
        self.client = TestClient(router)

        # Buat Supervisor
        self.supervisor = User.objects.create_user(username='supervisor', password='password', is_staff=True)
        self.supervisor_profile, _ = UserProfile.objects.get_or_create(user=self.supervisor)

        # Buat Worker dengan Supervisor
        self.user = User.objects.create_user(username='userA', password='abc123')
        self.worker = Worker.objects.create(user=self.user, assigned_supervisor=self.supervisor_profile)

        self.pond = Pond.objects.create(
            owner=self.supervisor,
            name='Test Pond',
            image_name='test_pond.png',
            length=10.0,
            width=5.0,
            depth=2.0
        )

        start_time = make_aware(datetime.now()) - timedelta(days=30)
        end_time = start_time + timedelta(days=60)
        self.cycle = Cycle.objects.create(
            supervisor=self.supervisor,
            start_date=start_time,
            end_date=end_time,
        )

        self.fish_sampling = FishSampling.objects.create(
            pond=self.pond,
            reporter=self.user,
            cycle=self.cycle,
            fish_weight=1.5,
            fish_length=25.0,
            recorded_at=make_aware(datetime.now())
        )

        # FIXED
        self.token = str(AccessToken.for_user(self.user))
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def test_add_fish_sampling(self):
        response = self.client.post(
            f'/{self.pond.pond_id}/{self.cycle.id}/',
            data=json.dumps({'fish_weight': 2.0, 'fish_length': 30.0}),
            content_type="application/json",
            headers=self.headers
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertIn("pond_id", response.json())  
        self.assertEqual(response.json()["pond_id"], str(self.pond.pond_id))
        self.assertEqual(response.json()["reporter"]["id"], self.user.id)  
        self.assertEqual(response.json()["fish_weight"], 2.0)
        self.assertEqual(response.json()["fish_length"], 30.0)
        self.assertTrue(response.json()["recorded_at"]) 

    def test_add_fish_sampling_invalid_weight_length(self):
        response = self.client.post(
            f'/{self.pond.pond_id}/{self.cycle.id}/',
            data=json.dumps({'fish_weight': 12.0, 'fish_length': 110.0}),
            content_type="application/json",
            headers=self.headers
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())
        self.assertEqual(response.json()["error"], "Berat dan panjang ikan terlalu besar, harap pastikan data benar.")

    def test_create_fish_sampling_invalid_weight(self):
        response = self.client.post(
            f'/{self.pond.pond_id}/{self.cycle.id}/',
            data=json.dumps({'fish_weight': 11.0, 'fish_length': 50.0}),
            content_type="application/json",
            headers=self.headers
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())
        self.assertEqual(response.json()["error"], "Berat ikan lebih dari 10 kg, harap pastikan data benar.")

    def test_create_fish_sampling_invalid_length(self):
        response = self.client.post(
            f'/{self.pond.pond_id}/{self.cycle.id}/',
            data=json.dumps({'fish_weight': 5.0, 'fish_length': 110.0}),
            content_type="application/json",
            headers=self.headers
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())
        self.assertEqual(response.json()["error"], "Panjang ikan lebih dari 100 cm, harap pastikan data benar.")
    
    def test_add_fish_sampling_with_invalid_data(self):
        response = self.client.post(f'/{self.pond.pond_id}/{self.cycle.id}/', data=json.dumps({
            'fish_weight': 1.2,
            'fish_length': -10.0
        }), content_type='application/json', headers={"Authorization": f"Bearer {str(AccessToken.for_user(self.user))}"})
        self.assertEqual(response.status_code, 400) 
        self.assertEqual(response.json()['error'], 'Berat dan panjang ikan harus lebih dari 0')
        self.assertFalse(FishSampling.objects.filter(fish_weight=1.2, fish_length=-10.0).exists())

    def test_get_latest_fish_sampling(self):
        response = self.client.get(
            f'/{self.pond.pond_id}/{self.cycle.id}/latest/',
            headers={"Authorization": f"Bearer {str(AccessToken.for_user(self.user))}"}
        )

        self.assertEqual(response.json()['reporter']['phone_number'], self.fish_sampling.reporter.username)

        self.assertEqual(response.json()['fish_weight'], self.fish_sampling.fish_weight)
        self.assertEqual(response.json()['fish_length'], self.fish_sampling.fish_length)
        self.assertTrue(response.json()['recorded_at'])

    def test_get_latest_fish_sampling_no_data(self):
        FishSampling.objects.all().delete()
        response = self.client.get(f'/{self.pond.pond_id}/{self.cycle.id}/latest/', headers={"Authorization": f"Bearer {str(AccessToken.for_user(self.user))}"})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['detail'], 'Data tidak ditemukan')
    
    def test_get_latest_fish_sampling_cycle_not_active(self):
        starting_date = datetime.now() - timedelta(days=90)
        ending_date = starting_date + timedelta(days=60)
        cycle = Cycle.objects.create(
            supervisor=self.user,
            start_date=starting_date,
            end_date=ending_date
        )
        response = self.client.get(f'/{self.pond.pond_id}/{cycle.id}/latest/', headers={"Authorization": f"Bearer {str(AccessToken.for_user(self.user))}"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['detail'], 'Siklus tidak aktif')
    
    def test_get_fish_sampling_invalid_pond(self):
        response = self.client.get(f'/{uuid.uuid4()}/{self.cycle.id}/latest/', headers={"Authorization": f"Bearer {str(AccessToken.for_user(self.user))}"})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['detail'], 'Not Found')
    
    def test_list_fish_samplings_unauthorized(self):
        response = self.client.get(f'/{self.pond.pond_id}/', headers={})
        self.assertEqual(response.status_code, 401) 
    
    def test_list_fish_samplings(self):
     
        response = self.client.get(f'/{self.pond.pond_id}/', headers=self.headers)

        self.assertEqual(response.status_code, 200, "Status response seharusnya 200")

        # Ambil daftar fish samplings dari response API
        fish_samplings = response.json().get('fish_samplings', [])

        # Cek apakah jumlah fish samplings lebih dari 0
        self.assertGreaterEqual(len(fish_samplings), 1, "Fish sampling data kurang dari 1")

        # Cek data fish sampling pertama
        self.assertEqual(fish_samplings[0]['sampling_id'], str(self.fish_sampling.sampling_id))
        self.assertEqual(fish_samplings[0]['pond_id'], str(self.fish_sampling.pond.pond_id))

        # Cek data fish sampling kedua hanya jika ada cukup data
        if len(fish_samplings) > 1:
            self.assertEqual(fish_samplings[1]['sampling_id'], str(self.fish_sampling_userA.sampling_id))
            self.assertEqual(fish_samplings[1]['pond_id'], str(self.fish_sampling_userA.pond.pond_id))
        
        # Cek apakah cycle_id sesuai
        self.assertEqual(response.json()['cycle_id'], str(self.cycle.id))

    def test_list_fish_samplings_by_pond_invalid_cycle(self):
        invalid_pond_id = uuid.uuid4() 
        response = self.client.get(f'/{invalid_pond_id}/', headers=self.headers)
        self.assertEqual(response.status_code, 404) 

    def test_fish_death(self):
        response = self.client.post(
            f'/{self.pond.pond_id}/death/',
            data=json.dumps({
                'count': 10
            }),
            content_type="application/json",
            headers=self.headers
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['pond_id'], str(self.pond.pond_id))
        self.assertEqual(response.json()['reporter']['id'], self.user.id)  
        self.assertEqual(response.json()['count'], 10)
        self.assertTrue(response.json()['recorded_at'])

    def test_fish_death_with_invalid_data(self):
        response = self.client.post(f'/{self.pond.pond_id}/death/', data=json.dumps({
            'count': -10
        }), content_type='application/json', headers=self.headers)
        self.assertEqual(response.status_code, 400) 
        self.assertEqual(response.json()['detail'], 'Jumlah ikan mati harus minimal sama dengan 0')
        self.assertFalse(FishDeath.objects.filter(count=-10).exists())

    def test_fish_death_invalid_pond(self):
        response = self.client.post(f'/{uuid.uuid4()}/death/', data=json.dumps({
            'count': 10
        }), content_type='application/json', headers=self.headers)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['detail'], 'Not Found')

    def test_fish_death_unauthorized(self):
        response = self.client.post(f'/{self.pond.pond_id}/death/', data=json.dumps({
            'count': 10
        }), content_type='application/json', headers={})
        self.assertEqual(response.status_code, 401)

    def test_fish_death_cycle_not_active(self):
        starting_date = datetime.now() - timedelta(days=90)
        ending_date = starting_date + timedelta(days=60)
        cycle = Cycle.objects.create(
            supervisor=self.user,
            start_date=starting_date,
            end_date=ending_date
        )
        response = self.client.post(f'/{self.pond.pond_id}/death/', data=json.dumps({
            'count': 10
        }), content_type='application/json', headers=self.headers)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['detail'], 'Siklus tidak aktif')

    def test_get_latest_fish_death(self):
        response = self.client.get(
            f'/{self.pond.pond_id}/death/latest/',
            headers={"Authorization": f"Bearer {str(AccessToken.for_user(self.user))}"}
        )

        self.assertEqual(response.json()['reporter']['phone_number'], self.fish_death.reporter.username)
        self.assertEqual(response.json()['count'], self.fish_death.count)

    def test_get_latest_fish_death_no_data(self):
        FishDeath.objects.all().delete()
        response = self.client.get(f'/{self.pond.pond_id}/death/latest/', headers={"Authorization": f"Bearer {str(AccessToken.for_user(self.user))}"})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['detail'], 'Data tidak ditemukan')

    def test_get_latest_fish_death_cycle_not_active(self):
        starting_date = datetime.now() - timedelta(days=90)
        ending_date = starting_date + timedelta(days=60)
        cycle = Cycle.objects.create(
            supervisor=self.user,
            start_date=starting_date,
            end_date=ending_date
        )
        response = self.client.get(f'/{self.pond.pond_id}/death/latest/', headers={"Authorization": f"Bearer {str(AccessToken.for_user(self.user))}"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['detail'], 'Siklus tidak aktif')

    def test_get_fish_death_invalid_pond(self):
        response = self.client.get(f'/{uuid.uuid4()}/death/latest/', headers={"Authorization": f"Bearer {str(AccessToken.for_user(self.user))}"})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['detail'], 'Not Found')

    def test_list_fish_deaths_unauthorized(self):
        response = self.client.get(f'/{self.pond.pond_id}/death/', headers={})
        self.assertEqual(response.status_code, 401)

    def test_list_fish_deaths(self):
        response = self.client.get(f'/{self.pond.pond_id}/death/', headers=self.headers)

        self.assertEqual(response.status_code, 200, "Status response seharusnya 200")

        # Ambil daftar fish deaths dari response API
        fish_deaths = response.json().get('fish_deaths', [])

        # Cek apakah jumlah fish deaths lebih dari 0
        self.assertGreaterEqual(len(fish_deaths), 1, "Fish death data kurang dari 1")

        # Cek data fish death pertama
        self.assertEqual(fish_deaths[0]['death_report_id'], str(self.fish_death.death_report_id))
        self.assertEqual(fish_deaths[0]['pond_id'], str(self.fish_death.pond.pond_id))

        # Cek data fish death kedua hanya jika ada cukup data
        if len(fish_deaths) > 1:
            self.assertEqual(fish_deaths[1]['death_report_id'], str(self.fish_death_userA.death_report_id))
            self.assertEqual(fish_deaths[1]['pond_id'], str(self.fish_death_userA.pond.pond_id))

        # Cek apakah cycle_id sesuai
        self.assertEqual(response.json()['cycle_id'], str(self.cycle.id))

    def test_list_fish_deaths_by_pond_invalid_cycle(self):
        invalid_pond_id = uuid.uuid4()
        response = self.client.get(f'/{invalid_pond_id}/death/', headers=self.headers)
        self.assertEqual(response.status_code, 404)

    

    


    def test_get_fish_status_no_input_yet(self):
        """Menghapus semua FishSampling sebelum request untuk memastikan ObjectDoesNotExist tercapai"""
        FishSampling.objects.all().delete()
        response = self.client.get(
            f'/{self.pond.pond_id}/{self.cycle.id}/status/',
            headers=self.headers
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['detail'], "Data belum tersedia, silakan isi data terlebih dahulu")
    
    def test_get_fish_status_valid(self):
        """Menguji apakah status ikan dihitung dengan benar jika ada data fish sampling"""
        response = self.client.get(
            f'/{self.pond.pond_id}/{self.cycle.id}/status/',
            headers=self.headers
        )

        self.assertEqual(response.status_code, 200)
        expected_week = (make_aware(datetime.now()) - self.cycle.start_date).days // 7 + 1
        expected_status = determine_fish_status(expected_week, self.fish_sampling.fish_length, self.fish_sampling.fish_weight)
        self.assertEqual(response.json()['status'], expected_status)

class DetermineFishStatusTest(TestCase):
    def test_determine_fish_status_normal(self):
        """Pastikan ikan dikategorikan normal jika berada dalam margin 20% dari target"""
        self.assertEqual(determine_fish_status(1, 5.5, 0.002), "normal")  # Sesuai target
        self.assertEqual(determine_fish_status(1, 6.0, 0.0021), "normal")  # Sedikit di atas
        self.assertEqual(determine_fish_status(1, 5.0, 0.0019), "normal")  # Sedikit di bawah

    def test_determine_fish_status_abnormal_due_to_length(self):
        """Pastikan ikan dikategorikan abnormal jika panjang melebihi 20% target"""
        self.assertEqual(determine_fish_status(1, 7.0, 0.002), "abnormal")  # 27% lebih panjang
        self.assertEqual(determine_fish_status(1, 4.0, 0.002), "abnormal")  # 27% lebih pendek

    def test_determine_fish_status_abnormal_due_to_weight(self):
        """Pastikan ikan dikategorikan abnormal jika berat melebihi 20% target"""
        self.assertEqual(determine_fish_status(1, 5.5, 0.003), "abnormal")  # Berat lebih dari 20% target
        self.assertEqual(determine_fish_status(1, 5.5, 0.001), "abnormal")  # Berat kurang dari 20% target

    def test_determine_fish_status_invalid_week(self):
        """Pastikan jika week di luar 1-9, return invalid_week"""
        self.assertEqual(determine_fish_status(0, 5.5, 0.002), "invalid_week")
        self.assertEqual(determine_fish_status(10, 5.5, 0.002), "invalid_week")
        