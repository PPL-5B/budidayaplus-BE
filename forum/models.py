import uuid
from django.db import models
from django.contrib.auth.models import User

class Forum(models.Model):
    TAG_CHOICES = (
        ('ikan', 'Ikan'),
        ('kolam', 'Kolam'),
        ('siklus', 'Siklus'),
        ('budidayaplus', 'BudidayaPlus'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255, blank=True, default="")
    description = models.TextField()
    tag = models.CharField(max_length=12, choices=TAG_CHOICES, default='ikan')
    timestamp = models.DateTimeField(auto_now_add=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies'
    )

    def __str__(self):
        if self.parent:
            return f"Reply {self.id} by {self.user.username} to Forum {self.parent.id}"
        return f"Forum Post {self.id} – {self.title} by {self.user.username}"

    @property
    def upvotes(self):
        return self.votes.filter(vote_choice='up').count()

    @property
    def downvotes(self):
        return self.votes.filter(vote_choice='down').count()


class ForumVote(models.Model):
    VOTE_TYPE = (
        ('up', 'Upvote'),
        ('down', 'Downvote'),
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    forum = models.ForeignKey(Forum, on_delete=models.CASCADE, related_name='votes')
    vote_choice = models.CharField(max_length=4, choices=VOTE_TYPE)

    class Meta:
        unique_together = ('user', 'forum')