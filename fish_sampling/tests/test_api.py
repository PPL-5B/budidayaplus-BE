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

class FishSamplingAPITest(TestCase):
    def setUp(self):
        self.client = TestClient(router)

        # Buat Supervisor
        self.supervisor = User.objects.create_user(username='supervisor', password='password', is_staff=True)
        self.supervisor_profile, created = UserProfile.objects.get_or_create(user=self.supervisor)

        # Buat Worker dengan Supervisor
        self.user = User.objects.create_user(username='userA', password='abc123')
        self.worker = Worker.objects.create(user=self.user, assigned_supervisor=self.supervisor_profile)

        self.pond = Pond.objects.create(
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
        response = self.client.post(f'/{self.pond.pond_id}/{self.cycle.id}/', data=json.dumps({    
            'fish_weight': 2.0,
            'fish_length': 30.0
        }), content_type='application/json', headers={"Authorization": f"Bearer {str(AccessToken.for_user(self.user))}"})
        response = self.client.post(
            f'/{self.pond.pond_id}/{self.cycle.id}/',
            data=json.dumps({
                'fish_weight': 2.0,
                'fish_length': 30.0
            }),
            content_type="application/json",
            headers=self.headers
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['pond_id'], str(self.pond.pond_id))
        self.assertEqual(response.json()['reporter']['id'], self.user.id)  
        self.assertEqual(response.json()['fish_weight'], 2.0)
        self.assertEqual(response.json()['fish_length'], 30.0)
        self.assertTrue(response.json()['recorded_at'])
    
    def test_add_fish_sampling_with_invalid_data(self):
        response = self.client.post(f'/{self.pond.pond_id}/{self.cycle.id}/', data=json.dumps({
            'fish_weight': 1.2,
            'fish_length': -10.0
        }), content_type='application/json', headers={"Authorization": f"Bearer {str(AccessToken.for_user(self.user))}"})
        self.assertEqual(response.status_code, 400) 
        self.assertEqual(response.json()['detail'], 'Berat dan panjang ikan harus lebih dari 0')
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