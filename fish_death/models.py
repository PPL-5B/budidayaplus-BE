from django.db import models
from pond.models import Pond
from cycle.models import Cycle
from django.contrib.auth.models import User
import uuid

class FishDeath(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cycle = models.ForeignKey(Cycle, on_delete=models.CASCADE)
    pond = models.ForeignKey(Pond, on_delete=models.CASCADE)
    reporter = models.ForeignKey(User, on_delete=models.CASCADE)
    recorded_at = models.DateTimeField(auto_now_add=True)
    fish_death_count = models.IntegerField()
    fish_alive_count = models.IntegerField()

    def __str__(self):
        return str(self.id)