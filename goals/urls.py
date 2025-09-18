# goals/urls.py
from django.urls import path
from . import views

app_name = 'goals'
urlpatterns = [
    path('calculate/<int:participant_id>/', views.calculate_weekly_goals, name='calculate_weekly_goals'),
	path('send-weekly-message/<int:participant_id>/', views.send_weekly_message, name='send_weekly_message'),
]