# gdm/urls.py

from django.contrib import admin
from django.urls import path, include
from fitbit_integration import views as fitbit_views
from gdm import views as gdm_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('fitbit/', include('fitbit_integration.urls', namespace='fitbit_integration')),
    path('participant/<int:participant_id>/regenerate_token/', fitbit_views.regenerate_token, name='regenerate_token'),
    path('participant/<int:participant_id>/', fitbit_views.participant_detail, name='participant_detail'),

    # NEW: Google OAuth (server-side)
    path('google/start/<int:participant_id>/', gdm_views.google_oauth_start, name='google_oauth_start'),
    path('google/callback/', gdm_views.google_oauth_callback, name='google_oauth_callback'),
]