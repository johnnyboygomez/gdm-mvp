# project/auth_apps.py
from django.apps import AppConfig

class CustomAuthConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'django.contrib.auth'
    verbose_name = "T2D Groups"
