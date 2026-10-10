from django.conf import settings
from django.db import models


class Notification(models.Model):
    MATCH = 'MATCH'
    CLAIM = 'CLAIM'
    RECOVERY = 'RECOVERY'
    TYPE_CHOICES = [
        (MATCH, 'New match'),
        (CLAIM, 'Claim update'),
        (RECOVERY, 'Recovery'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    message = models.CharField(max_length=255)
    notification_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    link = models.CharField(max_length=200, blank=True)   # the page this notification opens
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']   # newest first

    def __str__(self):
        return f'{self.user.username}: {self.message[:40]}'