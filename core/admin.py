# core/admin.py
from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as DefaultUserAdmin
from django.utils.html import format_html, format_html_join
from device_integration.fitbit import fetch_fitbit_data_for_participant
from core.models import Participant
from django.urls import reverse
from django.utils import timezone
import json


###############
# Mixin with shared button methods
class ParticipantButtonMixin:
    def calculate_weekly_goals_button(self, obj):
        if obj.pk:
            url = reverse("goals:calculate_weekly_goals", args=[obj.pk])
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
# Inline for Participant
class ParticipantInline(ParticipantButtonMixin, admin.StackedInline):
    model = Participant
    can_delete = False
    extra = 0
    max_num = 1
    min_num = 1

    def render_json(self, value):
        """Format JSON data into readable HTML lists"""
        if not value:
            return "-"
        try:
            data = json.loads(value) if isinstance(value, str) else value
        except Exception:
            return value
        
        if isinstance(data, list):
            # reverse list for Managers
            data = list(reversed(data))
            return format_html_join(
                "", "<li>{}: {} steps</li>",
                ((d.get("dateTime"), d.get("value")) for d in data)
            )
        elif isinstance(data, dict):
            # sort by date descending
            items = sorted(data.items(), key=lambda x: x[0], reverse=True)
            return format_html_join(
                "", "<li>{}: increase {}, new target {}, avg {}</li>",
                ((date, info.get("increase"), info.get("new_target"), info.get("average_steps")) for date, info in items)
            )
        return value

    def get_fields(self, request, obj=None):
        """Customize visible fields based on user permissions"""
        base_fields = [
            'start_date',
            'email',
            #'weight',
            #'height',
        ]
        
        # Data fields - different for Managers vs Superusers
        if request.user.groups.filter(name="Managers").exists() and not request.user.is_superuser:
            # Managers see read-only display versions
            data_fields = ['daily_steps_display', 'targets_display']
        else:
            # Superusers see editable versions
            data_fields = ['daily_steps', 'targets']
        
        # Technical fields (always readonly)
        tech_fields = [
            'fitbit_user_id',
            'fitbit_access_token', 
            'fitbit_refresh_token',
            'fitbit_token_expires',
            'fitbit_auth_token',
            'device_type',
            'fetch_fitbit_data_button',
            'authenticate_fitbit_button',
            'calculate_weekly_goals_button',
        ]
        
        return base_fields + data_fields + tech_fields

    def get_readonly_fields(self, request, obj=None):
        """Set readonly fields based on user permissions"""
        self.request = request
        print(f"User: {self.request.user}")
        base_readonly = [
            'fitbit_user_id', 'fitbit_access_token', 'fitbit_refresh_token',
            'fitbit_token_expires', 'fitbit_auth_token', 'device_type',
            'fetch_fitbit_data_button', 'authenticate_fitbit_button',
            'calculate_weekly_goals_button'
        ]

        if request.user.groups.filter(name="Managers").exists() and not request.user.is_superuser:
            # Managers: display methods are readonly
            return base_readonly + ['daily_steps_display', 'targets_display']
        else:
            # Superusers: technical fields are readonly, data fields are editable
            return base_readonly

    def daily_steps_display(self, obj):
        """Display formatted daily steps for Managers"""
        print(f"=== DAILY STEPS DISPLAY DEBUG ===")
        print(f"Has request: {hasattr(self, 'request')}")
        if hasattr(self, 'request'):
            print(f"User: {self.request.user}")
            print(f"Is in Managers group: {self.request.user.groups.filter(name='Managers').exists()}")
            print(f"Is superuser: {self.request.user.is_superuser}")
        
        if getattr(self, 'request', None) and self.request.user.groups.filter(name="Managers").exists() \
        and not self.request.user.is_superuser:
            print("Formatting JSON for Manager")
            formatted = self.render_json(obj.daily_steps)
            print(f"Formatted result: {formatted}")
            return format_html("<ul style='margin:0 0 0 1em;'>{}</ul>", formatted)
        else:
            print("Returning raw JSON")
            return obj.daily_steps

    def targets_display(self, obj):
        """Display formatted targets for Managers"""
        print(f"=== TARGETS DISPLAY DEBUG ===")
        if getattr(self, 'request', None) and self.request.user.groups.filter(name="Managers").exists() \
        and not self.request.user.is_superuser:
            print("Formatting JSON for Manager")
            formatted = self.render_json(obj.targets)
            return format_html("<ul style='margin:0 0 0 1em;'>{}</ul>", formatted)
        else:
            print("Returning raw JSON")
            return obj.targets

###############
# Custom User Admin
class CustomUserAdmin(DefaultUserAdmin):
    inlines = [ParticipantInline]

    def get_fieldsets(self, request, obj=None):
        """Customize fieldsets based on user permissions"""
        fieldsets = super().get_fieldsets(request, obj)
        
        # Check if user is in Managers group (but not superuser)
        if (request.user.groups.filter(name='Managers').exists() and 
            not request.user.is_superuser):
            # Return only basic user info (username/password) for Managers
            return (
                (None, {
                    'fields': ('username', 'password')
                }),
            )
        
        # Return full fieldsets for superusers
        return fieldsets


###############
# Register the custom User admin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)