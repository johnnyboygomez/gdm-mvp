# core/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DefaultUserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.urls import path
from django.urls import reverse
from django.shortcuts import redirect
from core.models import Participant
from fitbit_integration.utils import regenerate_fitbit_token
from django.utils.html import format_html


# Participant admin
class ParticipantAdmin(admin.ModelAdmin):
    readonly_fields = ('fitbit_auth_token', 'authorize_fitbit_button')

    def authorize_fitbit_button(self, obj):
        if not obj.pk:
            return "Save participant to get the Fitbit authorization link."
        url = reverse('fitbit_integration:authorize_fitbit') + f'?state={obj.fitbit_auth_token}'
        return format_html('<a class="button" href="{}" target="_blank">Authorize Fitbit</a>', url)
    authorize_fitbit_button.short_description = "Fetch New Fitbit Access and Refresh Tokens"

admin.site.register(Participant, ParticipantAdmin)


# Inline to edit Participant info inside User admin
class ParticipantInline(admin.StackedInline):
    model = Participant
    can_delete = False
    verbose_name_plural = 'Participant Info'

# Custom User admin to restrict Managers/RAs
class CustomUserAdmin(DefaultUserAdmin):
    inlines = (ParticipantInline,)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.groups.filter(name='Managers/RAs').exists():
            # Managers/RAs only see non-admin users (not staff or superuser)
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

# Unregister default User admin and register your custom one
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
