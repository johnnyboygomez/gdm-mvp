# core/models.py

from django.contrib.auth.models import User
from django.db import models
import uuid

class Participant(models.Model):
    # OLD
    # user = models.OneToOneField(User, on_delete=models.CASCADE)

    # NEW
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)    
    start_date = models.DateField()
    email = models.EmailField(unique=True)
    weight = models.FloatField(null=True, blank=True)   # kg or lbs, specify later
    height = models.FloatField(null=True, blank=True)   # cm or inches, specify later
    daily_steps = models.JSONField(default=dict, blank=True)  # {date: steps}
    targets = models.JSONField(default=dict, blank=True)      # e.g. {"steps": 10000, "calories": 2000}
    
    # Fitbit OAuth tokens etc
    fitbit_user_id = models.CharField(max_length=100, blank=True, null=True)
    fitbit_access_token = models.TextField(null=True, blank=True)
    fitbit_refresh_token = models.TextField(null=True, blank=True)
    fitbit_token_expires = models.DateTimeField(null=True, blank=True)
    fitbit_auth_token = models.UUIDField(default=uuid.uuid4, unique=True)
    
    #Google stuff
    google_id = models.CharField(max_length=255, blank=True, null=True)
    google_email = models.EmailField(blank=True, null=True)
    
    google_access_token = models.TextField(blank=True, null=True)
    google_refresh_token = models.TextField(blank=True, null=True)
    google_token_expiry = models.DateTimeField(blank=True, null=True)


    def __str__(self):
    	return f"{self.user.username} ({self.user.email})"

    def save(self, *args, **kwargs):
        # --- NEW: default email to username if empty ---
        if not self.email and self.user:
            self.email = self.user.username
        # -----------------------------------------------
        super().save(*args, **kwargs)