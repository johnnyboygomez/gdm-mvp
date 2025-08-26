# core/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DefaultUserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.urls import path, reverse
from django.shortcuts import redirect, render, get_object_or_404
from django.http import JsonResponse
import requests
from core.models import Participant
from fitbit_integration.utils import regenerate_fitbit_token
from datetime import date, timedelta
from django.conf import settings


###############
# Participant Admin
class ParticipantAdmin(admin.ModelAdmin):
    readonly_fields = ('fitbit_auth_token', 'authorize_fitbit_button')
    # Add this so admin shows the user dropdown/search properly
    raw_id_fields = ('user',)
    def has_module_permission(self, request):
        # Only superusers see the module in the left menu
        return request.user.is_superuser

    def authorize_fitbit_button(self, obj):
        if not obj.pk:
            return "Save the user first to fetch Fitbit tokens."
        url = reverse('fitbit_integration:authorize_fitbit') + f'?state={obj.fitbit_auth_token}'
        return format_html('<a class="button" href="{}" target="_blank">Authorize Fitbit</a>', url)
    authorize_fitbit_button.short_description = "Fetch New Fitbit Access and Refresh Tokens"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'fetch-fitbit-data/<int:participant_id>/',
                self.admin_site.admin_view(self.fetch_fitbit_data),
                name='fetch_fitbit_data',
            ),
            path(
                'show-weekly-data/<int:participant_id>/',
                self.admin_site.admin_view(self.show_weekly_data),
                name='show_weekly_data',
            ),
        ]
        return custom_urls + urls

    def fetch_fitbit_data(self, request, participant_id):
        participant = get_object_or_404(Participant, pk=participant_id)
        access_token = participant.fitbit_access_token
        if not access_token:
            return JsonResponse({"error": "No Fitbit access token found"}, status=400)
        start_date = participant.start_date
        if not start_date:
            return JsonResponse({"error": "No start date defined for participant"}, status=400)
        end_date = start_date + timedelta(days=1095)

        # Fitbit API requires yyyy-MM-dd format
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')

        # Example endpoint: get all activities for all time
        # You may need to loop over dates or use the Fitbit API endpoint that returns full history
        url = f"https://api.fitbit.com/1/user/-/activities/steps/date/{start_str}/{end_str}.json"
        headers = {"Authorization": f"Bearer {access_token}"}

        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return JsonResponse({
                "error": "Failed to fetch Fitbit data",
                "details": response.text
            }, status=response.status_code)

        data = response.json()
        # Filter out days where steps = 0
        filtered_steps = [
            entry for entry in data.get("activities-steps", [])
            if int(entry.get("value", 0)) > 0
        ]
            
        # Save filtered steps into Participant
        participant.daily_steps = filtered_steps
        participant.save()

        return JsonResponse(filtered_steps, safe=False)
       ####return JsonResponse(data, safe=False)
    def show_weekly_data(self, request, participant_id):
        participant = get_object_or_404(Participant, pk=participant_id)

        # For now, just return whatever is in daily_steps
        if not participant.daily_steps:
            return JsonResponse({"error": "No daily_steps data found"}, status=404)

        return JsonResponse(participant.daily_steps, safe=False)


# Register Participant so reverse('admin:core_participant_change') works
admin.site.register(Participant, ParticipantAdmin)

###############
# Inline for User admin
class ParticipantInline(admin.StackedInline):
    model = Participant
    can_delete = False
    verbose_name_plural = "Participant Info"
    raw_id_fields = ('user',)
    extra = 0  # Prevent extra empty inlines by default
    max_num = 1
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
        'google_id',
        'google_email',
        'authorize_google_button',
    )

    fields = (
        # Participant fields
        'start_date',
        'email',
        'weight',
        'height',
        'daily_steps',
        'targets',
        # Fitbit fields
        'fitbit_user_id',
        'fitbit_auth_token',
        'fitbit_access_token',
        'fitbit_refresh_token',
        'fitbit_token_expires',
        'authorize_fitbit_button',
        'fetch_fitbit_data_button',
        'show_weekly_data_button',
        'authorize_google_button', 
    )

    def get_extra(self, request, obj=None, **kwargs):
        """
        Only allow one participant inline per user.
        If a participant exists, show 0 extra forms.
        If none exists yet, show 1 form to create it.
        """
        if obj and Participant.objects.filter(user=obj).exists():
            return 0
        return 1

    def has_add_permission(self, request, obj=None):
        """Prevent adding more than one participant per user."""
        if obj and Participant.objects.filter(user=obj).exists():
            return False
        return super().has_add_permission(request, obj=obj)

    def authorize_fitbit_button(self, obj):
        url = reverse('fitbit_integration:authorize_fitbit') + f'?state={obj.fitbit_auth_token}'
        return format_html('<a class="button" href="{}" target="_blank">Authorize Fitbit</a>', url)
    authorize_fitbit_button.short_description = "Fetch New Fitbit Access and Refresh Tokens"

    def fetch_fitbit_data_button(self, obj):
        if not obj.pk:
            return "Save participant first to fetch Fitbit data."
        
        # URL points to a custom admin view
        url = reverse('admin:fetch_fitbit_data', args=[obj.pk])
        return format_html(
            '<a class="button" href="{}" target="_blank">Fetch Fitbit Data</a>', url)

    fetch_fitbit_data_button.short_description = "Fetch Fitbit Data"

    def authorize_google_button(self, obj):
        if not obj.pk:
            return "Save participant first to authorize Google."
        url = reverse('google_oauth_start', args=[obj.pk])
        return format_html('<a class="button" href="{}">Authorize Google</a>', url)

    authorize_google_button.short_description = "Authorize Google Sign-In"


    def show_weekly_data_button(self, obj):
        if not obj.pk:
            return "Save participant first to show weekly data."
        
        url = reverse('admin:show_weekly_data', args=[obj.pk])
        return format_html(
            '<a class="button" href="{}" target="_blank">Show Weekly Data</a>', url)

    show_weekly_data_button.short_description = "Show Weekly Data"


###############
# Custom User Admin
class CustomUserAdmin(DefaultUserAdmin):
    inlines = (ParticipantInline,)

    class Media:
        css = {
            'all': ('core/admin.css',)
        }
        js = ('core/admin.js',)

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
        # Participant + Fitbit fields will appear here via inline
        ('Permissions', {
            'classes': ('collapse'),
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),'description': '<a id="toggle-permissions">Show Permissions</a>'
}),

    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.groups.filter(name='Managers/RAs').exists():
            return qs.filter(is_staff=False, is_superuser=False)
        return qs

    def has_delete_permission(self, request, obj=None):
        if request.user.groups.filter(name='Managers/RAs').exists():
            return False
        return super().has_delete_permission(request, obj=obj)

    def has_change_permission(self, request, obj=None):
        if request.user.groups.filter(name='Managers/RAs').exists():
            if obj is not None and (obj.is_staff or obj.is_superuser):
                return False
        return super().has_change_permission(request, obj=obj)

    def has_add_permission(self, request):
        if request.user.groups.filter(name='Managers/RAs').exists():
            return True
        return super().has_add_permission(request)
    
    def save_formset(self, request, form, formset, change):
        # Check each inline instance
        instances = formset.save(commit=False)
        for obj in instances:
            if obj.user_id is None:  # <-- only set if missing
                obj.user = form.instance
            obj.save()
        formset.save_m2m()
    def get_inline_instances(self, request, obj=None):
# Prevent Django from showing a blank participant inline when creating a new user.
#Only show the inline if the user object exists.
        inline_instances = []
        if obj:  # Only show inlines for existing users
            for inline_class in self.inlines:
                inline = inline_class(self.model, self.admin_site)
                inline_instances.append(inline)
        return inline_instances


# Replace default User admin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)