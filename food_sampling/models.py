from django.db import models
from pond.models import Pond
from cycle.models import Cycle
from django.contrib.auth.models import User
import uuid
from notifications.models import Notification


class FoodSampling(models.Model):
    sampling_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cycle = models.ForeignKey(Cycle, on_delete=models.CASCADE)
    pond = models.ForeignKey(Pond, on_delete=models.CASCADE)
    reporter = models.ForeignKey(User, on_delete=models.CASCADE)
    food_quantity = models.FloatField()
    recorded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.sampling_id)

# hello ngetes sonar

def fish_death_notification(models.Model):
    count = models.IntegerField()
    report_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cycle = models.ForeignKey(Cycle, on_delete=models.CASCADE)
    pond = models.ForeignKey(Pond, on_delete=models.CASCADE)
    reporter = models.ForeignKey(User, on_delete=models.CASCADE)
    food_quantity = models.FloatField()
    recorded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.report_id)
    title = 'Laporan Jumlah Kematian Ikan'
    message = f'Sebanyak {count} ekor ikan dilaporkan mati pada {recorded_at}'
    notification = Notification.objects.create(
        title=title,
        message=message,
        date=recorded_at,
        pond=pond,
        cycle=cycle,
    )

    def __str__(self):
        return str(self.sampling_id)
  