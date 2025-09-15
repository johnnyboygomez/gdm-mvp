# core/admin_dashboard_views.py

from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from .models import Participant

@staff_member_required
def dashboard_view(request):
    is_superuser = request.user.is_superuser
    is_manager = request.user.groups.filter(name="Managers").exists() and not is_superuser
    participants = Participant.objects.select_related('user').all().order_by('start_date')
    
    context = {
        "is_superuser": is_superuser,
        "is_manager": is_manager,
        "participants": participants,
        "user": request.user,
    }
    return render(request, "admin/dashboard.html", context)
  