# gdm/urls.py

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('fitbit/', include('device_integration.urls', namespace='device_integration')),
    path('goals/', include('goals.urls')),
]
