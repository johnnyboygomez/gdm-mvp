# core/signals.py
#from django.contrib.auth.models import User
#from django.db.models.signals import post_save
#from django.dispatch import receiver
#from core.models import Participant
#from django.utils import timezone

#@receiver(post_save, sender=User)
#def create_or_update_participant(sender, instance, created, **kwargs):
#    """Ensure every user has exactly one participant"""
#    # Skip if participant already exists (handles admin inline case)
#    if Participant.objects.filter(user=instance).exists():
#        return
        
    # Only create for new users
 #   if created:
 #       Participant.objects.get_or_create(
 #           user=instance,
 #           defaults={
 #               'start_date': timezone.now().date(),
 #               'email': instance.email or ''
 #           }
 #       )