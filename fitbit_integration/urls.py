# fitbit_integration/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('authorize/', views.authorize_fitbit, name='authorize_fitbit'),
    path('callback/', views.fitbit_callback, name='fitbit_callback'),
    path('', views.index, name='fitbit_home'),
]
	
