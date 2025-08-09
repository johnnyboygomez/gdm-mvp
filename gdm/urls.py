# gdm/urls.py

from django.contrib import admin
from django.urls import path, include
from fitbit_integration import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('fitbit/', include('fitbit_integration.urls', namespace='fitbit_integration')),
    path('participant/<int:participant_id>/regenerate_token/', views.regenerate_token, name='regenerate_token'),
    path('participant/<int:participant_id>/', views.participant_detail, name='participant_detail'),

	]
