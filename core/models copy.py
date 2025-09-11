# core/models.py

from django.contrib.auth.models import User
from django.db import models
from django.conf import settings
import uuid

class Participant(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)  # <-- changed
    start_date = models.DateField()
    email = models.EmailField(unique=True)
    # weight = models.FloatField(null=True, blank=True)
    # height = models.FloatField(null=True, blank=True)
    daily_steps = models.JSONField(default=dict, blank=True)
    targets = models.JSONField(default=dict, blank=True)

    # Device type
    device_type = models.CharField(
        max_length=50,
        default=getattr(settings, 'DEFAULT_DEVICE_TYPE', 'fitbit')  # fallback to 'fitbit'
    )
    
    # Fitbit OAuth tokens
    fitbit_user_id = models.CharField(max_length=100, blank=True, null=True)
    fitbit_access_token = models.TextField(null=True, blank=True)
    fitbit_refresh_token = models.TextField(null=True, blank=True)
    fitbit_token_expires = models.DateTimeField(null=True, blank=True)
    fitbit_auth_token = models.UUIDField(default=uuid.uuid4, unique=True)

    def __str__(self):
        return f"{self.user.username if self.user else 'No User'} ({self.email})"

    def save(self, *args, **kwargs):
        if not self.email and self.user:
            self.email = self.user.username
        super().save(*args, **kwargs)
