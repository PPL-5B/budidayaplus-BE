import uuid
from django.db import models
from django.contrib.auth.models import User

class Forum(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')

    def __str__(self):
        if self.parent:
            return f"Reply {self.id} by {self.user.username} to Forum {self.parent.id}"
        return f"Forum Post {self.id} by {self.user.username}"
