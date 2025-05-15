from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied, ValidationError
from user_profile.models import UserProfile, Worker
from user_profile.services.create_worker_service_impl import CreateWorkerServiceImpl

class PayloadMock:
    def __init__(self, phone_number, password, first_name, last_name):
        self.phone_number = phone_number
        self.password = password
        self.first_name = first_name
        self.last_name = last_name

class CreateWorkerServiceTest(TestCase):
    def setUp(self):
        # Buat supervisor dengan is_staff=True
        self.supervisor = User.objects.create_user(
            username='supervisor',
            password='pass',
            is_staff=True
        )
        # Pastikan UserProfile tidak menyebabkan duplikasi
        self.supervisor_profile, _ = UserProfile.objects.get_or_create(user=self.supervisor)

        self.payload = PayloadMock(
            phone_number='08123456789',
            password='password123',
            first_name='John',
            last_name='Doe'
        )

    def test_create_worker_success(self):
        """Should create new worker when supervisor is valid and phone is unique"""
        worker = CreateWorkerServiceImpl.create_worker(self.payload, self.supervisor)

        self.assertIsInstance(worker, Worker)
        self.assertEqual(worker.user.username, self.payload.phone_number)
        self.assertEqual(worker.assigned_supervisor, self.supervisor_profile)

    def test_create_worker_permission_denied(self):
        """Should raise PermissionDenied if supervisor is not staff"""
        not_supervisor = User.objects.create_user(
            username='regularuser',
            password='password',
            is_staff=False
        )
        with self.assertRaises(PermissionDenied):
            CreateWorkerServiceImpl.create_worker(self.payload, not_supervisor)

    def test_create_worker_duplicate_phone(self):
        """Should raise ValidationError if phone number already exists"""
        # Buat user dengan nomor telepon yang sama lebih dulu
        User.objects.create_user(username=self.payload.phone_number, password='pass123')
        with self.assertRaises(ValidationError):
            CreateWorkerServiceImpl.create_worker(self.payload, self.supervisor)
