# core/models.py

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.conf import settings
import uuid

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
            
        return self.create_user(email, password, **extra_fields)

class CustomUser(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    objects = CustomUserManager() 
    
class Participant(models.Model):
    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('fr', 'Français'),
    ]
    
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    start_date = models.DateField()
    daily_steps = models.JSONField(default=dict, blank=True)
    targets = models.JSONField(default=dict, blank=True)
    
    language = models.CharField(
        max_length=2, 
        choices=LANGUAGE_CHOICES, 
        default='en',
        verbose_name='Language'
    )
    
    message_history = models.JSONField(default=list, blank=True, help_text="History of messages sent to participant")
    
    device_type = models.CharField(
        max_length=50,
        default=getattr(settings, 'DEFAULT_DEVICE_TYPE', 'fitbit')
    )
    fitbit_user_id = models.CharField(max_length=100, blank=True, null=True)
    fitbit_access_token = models.TextField(null=True, blank=True)
    fitbit_refresh_token = models.TextField(null=True, blank=True)
    fitbit_token_expires = models.DateTimeField(null=True, blank=True)
    fitbit_auth_token = models.UUIDField(default=uuid.uuid4, unique=True)
    
    def __str__(self):
        return f"{self.user.email} ({self.get_language_display()})"
    
    @property
    def email(self):
        return self.user.email