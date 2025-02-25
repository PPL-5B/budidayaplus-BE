from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied, ValidationError
from user_profile.models import UserProfile, Worker
from user_profile.services.create_worker_service import CreateWorkerService
from django.db import transaction


class CreateWorkerServiceImpl(CreateWorkerService):
    @staticmethod
    def create_worker(payload_worker, supervisor):
        if not supervisor.is_staff:
            raise PermissionDenied()

        if User.objects.filter(username=payload_worker.phone_number).exists():
            raise ValidationError("Nomor telefon sudah digunakan")

        with transaction.atomic():
            new_user = User.objects.create_user(
                username=payload_worker.phone_number,
                password=payload_worker.password,
                first_name=payload_worker.first_name,
                last_name=payload_worker.last_name,
            )

            supervisor_profile = UserProfile.objects.get(user=supervisor)

            return Worker.objects.create(
                image_name='',
                user=new_user,
                assigned_supervisor=supervisor_profile
            )
