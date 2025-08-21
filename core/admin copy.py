# core/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DefaultUserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.urls import path, reverse
from django.shortcuts import redirect, render, get_object_or_404

from core.models import Participant
from fitbit_integration.utils import regenerate_fitbit_token

###############
# Participant Admin
class ParticipantAdmin(admin.ModelAdmin):
    readonly_fields = ('fitbit_auth_token', 'authorize_fitbit_button', 'view_profile_button')

    def has_module_permission(self, request):
        # Only superusers see the module in the left menu
        return request.user.is_superuser

    def authorize_fitbit_button(self, obj):
        if not obj.fitbit_auth_token:
            return "Fitbit token not set."
        url = reverse('fitbit_integration:authorize_fitbit') + f'?state={obj.fitbit_auth_token}'
        return format_html('<a class="button" href="{}" target="_blank">Authorize Fitbit</a>', url)

    authorize_fitbit_button.short_description = "Fetch New Fitbit Access and Refresh Tokens"

    def view_profile_button(self, obj):
        if not obj.pk:
            return "Save participant to view profile."
        url = reverse('admin:core_participant_change', args=[obj.pk])
        return format_html('<a class="button" href="{}" target="_blank">View Participant Profile</a>', url)
    view_profile_button.short_description = "Participant Profile"

# Register Participant so reverse('admin:core_participant_change') works
admin.site.register(Participant, ParticipantAdmin)

###############
# Inline for User admin
class ParticipantInline(admin.StackedInline):
    model = Participant
    can_delete = False
    verbose_name_plural = "Participant Info"

    readonly_fields = (
        'fitbit_user_id',
        'fitbit_auth_token',
        'fitbit_access_token',
        'fitbit_refresh_token',
        'fitbit_token_expires',
        'daily_steps',
        'targets',
        'authorize_fitbit_button',
        'view_profile_button',
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
        'view_profile_button',
    )

    def authorize_fitbit_button(self, obj):
        if not obj.fitbit_auth_token:
            return "Fitbit token not set."
        url = reverse('fitbit_integration:authorize_fitbit') + f'?state={obj.fitbit_auth_token}'
    
        return format_html('<a class="button" href="{}" target="_blank">Authorize Fitbit</a>', url)

    authorize_fitbit_button.short_description = "Fetch New Fitbit Access and Refresh Tokens"

    def view_profile_button(self, obj):
        if not obj.pk:
            return "Save participant to view profile."
        url = reverse('admin:core_participant_change', args=[obj.pk])
        return format_html('<a class="button" href="{}" target="_blank">View Participant Profile</a>', url)
    view_profile_button.short_description = "Participant Profile"

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
        (None, {'fields': ('username', 'email', 'password')}),
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

# Replace default User admin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)