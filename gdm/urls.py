# gdm/urls.py

from django.contrib import admin
from django.urls import path, include
from core.admin_dashboard_views import dashboard_view, participant_detail_view

urlpatterns = [
    path('admin/dashboard/', dashboard_view, name='admin-dashboard'),
    path('admin/participant/<int:participant_id>/', participant_detail_view, name='participant_detail'),
    path('admin/', admin.site.urls),
    path('fitbit/', include('device_integration.urls', namespace='device_integration')),
    path('goals/', include('goals.urls')),
]