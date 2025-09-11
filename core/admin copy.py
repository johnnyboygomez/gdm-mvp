# core/admin.py

from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as DefaultUserAdmin
from django.utils.html import format_html
from device_integration.fitbit import fetch_fitbit_data_for_participant
from core.models import Participant
from django.urls import reverse

###############
# Inline for Participant
class ParticipantInline(admin.StackedInline):
    model = Participant
    can_delete = False
    extra = 0
    readonly_fields = ('fitbit_user_id', 'fitbit_access_token', 'fitbit_refresh_token', 'fitbit_token_expires', 'fitbit_auth_token', 'device_type', 'fetch_fitbit_data_button', 'authenticate_fitbit_button','calculate_weekly_goals_button')

    def calculate_weekly_goals_button(self, obj):
        if obj.pk:
            url = reverse("goals:calculate_weekly_goals", args=[obj.pk])  # Note: goals app
            return format_html(
                '<a class="button" href="{}" target="_blank">Calculate Weekly Goals</a>', url
            )
        return "Save participant first"
    
    
    def fetch_fitbit_data_button(self, obj):
        if obj.pk:
            url = reverse("device_integration:fetch_fitbit_data", args=[obj.pk])
            return format_html(
                '<a class="button" href="{}" target="_blank">Fetch Fitbit Data</a>', url
            )
        return "Save participant first"

    fetch_fitbit_data_button.short_description = "Fetch Fitbit Data"
    
    def authenticate_fitbit_button(self, obj):
        if obj.pk:
            url = reverse("device_integration:fitbit_auth_start", args=[obj.pk])
            return format_html(
                '<a class="button" href="{}" target="_blank">Authenticate Fitbit</a>', url
            )
        return "Save participant first"

    authenticate_fitbit_button.short_description = "Fitbit Authentication"

###############
# Custom UserAdmin
class UserAdmin(DefaultUserAdmin):
    inlines = [ParticipantInline]

    

    # Override save_model to ensure each user has exactly one Participant
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Check if user already has a participant
        if not Participant.objects.filter(user=obj).exists():
            Participant.objects.create(user=obj)

###############
# Unregister default User and register custom admin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
