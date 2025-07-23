# core/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DefaultUserAdmin
from django.contrib.auth.models import User
from .models import Participant

# Your existing Participant admin
@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ('user', 'email', 'start_date')
    search_fields = ('user__username', 'user__email')

    def email(self, obj):
        return obj.user.email

class ParticipantAdmin(admin.ModelAdmin):
    list_display = ('user', 'email', 'start_date')
    search_fields = ('user__username', 'user__email')

    def email(self, obj):
        return obj.user.email

    def has_add_permission(self, request):
        # Return False to hide the "+ Add" button in the Participants admin page
        # but the menu link remains visible.
        return False



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
