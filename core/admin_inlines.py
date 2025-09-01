from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from core.models import Participant, DeviceAccount

###############
# DeviceAccount Inline
class DeviceAccountInline(admin.TabularInline):
    model = DeviceAccount
    extra = 0
    max_num = 3
    can_delete = True
    readonly_fields = (
        'device_type',
        'auth_token',
        'access_token',
        'refresh_token',
        'token_expires',
        'authorize_device_button',
        'fetch_data_button',
        'show_weekly_data_button',
    )
    fields = readonly_fields

    def authorize_device_button(self, obj):
        if not obj.pk:
            return "Save participant first to authorize device."
        url = reverse('admin:core_user_authorize_device', args=[obj.pk])
        return format_html('<a class="button" href="{}" target="_blank">Authorize Device</a>', url)

    def fetch_data_button(self, obj):
        if not obj.pk:
            return "Save participant first to fetch device data."
        url = reverse('admin:core_user_fetch_device_data', args=[obj.pk])
        return format_html('<a class="button" href="{}" target="_blank">Fetch Data</a>', url)

    def show_weekly_data_button(self, obj):
        if not obj.pk:
            return "Save participant first to show weekly data."
        url = reverse('admin:core_user_show_device_weekly_data', args=[obj.pk])
        return format_html('<a class="button" href="{}" target="_blank">Show Weekly Data</a>', url)


###############
# Participant Inline
class ParticipantInline(admin.StackedInline):
    model = Participant
    can_delete = False
    raw_id_fields = ('user',)
    extra = 0
    max_num = 1
    inlines = [DeviceAccountInline]  # Nested inline
    readonly_fields = (
        'fitbit_user_id',
        'fitbit_auth_token',
        'fitbit_access_token',
        'fitbit_refresh_token',
        'fitbit_token_expires',
        'daily_steps',
        'targets',
        'authorize_fitbit_button',
        'fetch_fitbit_data_button',
        'show_weekly_data_button',
        'add_device_button',
    )
    fields = ('start_date', 'email', 'weight', 'height') + readonly_fields

    # Fitbit buttons
    def authorize_fitbit_button(self, obj):
        url = reverse('fitbit_integration:authorize_fitbit') + f'?state={obj.fitbit_auth_token}'
        return format_html('<a class="button" href="{}" target="_blank">Authorize Fitbit</a>', url)

    def fetch_fitbit_data_button(self, obj):
        if not obj or not obj.pk:
            return "Save participant first to fetch Fitbit Data."
        url = reverse('admin:core_user_fetch_fitbit_data', args=[obj.pk])
        return format_html('<a class="button" href="{}" target="_blank">Fetch Fitbit Data</a>', url)

    def show_weekly_data_button(self, obj):
        if not obj or not obj.pk:
            return "Save participant first to show weekly data."
        url = reverse('admin:core_user_show_weekly_data', args=[obj.pk])
        return format_html('<a class="button" href="{}" target="_blank">Show Weekly Data</a>', url)

    def add_device_button(self, obj):
        if not obj or not obj.pk:
            return "Save participant first to add device account."
        url = reverse('admin:core_user_add_device', args=[obj.pk])
        return format_html('<a class="button" href="{}" target="_blank">Add Device Account</a>', url)
