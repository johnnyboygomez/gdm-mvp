# core/signals.py
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from core.models import Participant
from django.utils import timezone
import uuid

@receiver(post_save, sender=User)
def create_or_update_participant(sender, instance, created, **kwargs):
    if created:
        # Create Participant with default values
        Participant.objects.create(
            user=instance,
            start_date=timezone.now().date(),
            fitbit_auth_token=str(uuid.uuid4()),  # generate token for callback
        )
    else:
        # Optional: update participant fields if needed
        Participant.objects.get_or_create(user=instance)
