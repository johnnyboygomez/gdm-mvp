# core/models.py

from django.contrib.auth.models import User
from django.db import models

class Participant(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
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

    def __str__(self):
    	return f"{self.user.username} ({self.user.email})"

