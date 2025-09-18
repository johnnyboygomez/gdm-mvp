# goals/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import HttpResponse
from core.models import Participant
from .targets import run_weekly_algorithm
from goals.notifications import send_goal_notification
from datetime import date, timedelta


def calculate_weekly_goals(request, participant_id):
    participant = get_object_or_404(Participant, pk=participant_id)
    
    try:
        result = run_weekly_algorithm(participant)
        
        if result:
            context = {
                "success": True,
                "participant_id": participant.id,
                "message": f"Weekly goal calculated: {result['new_target']} steps",
                "goal_data": result
            }
        else:
            context = {
                "success": False,
                "error": "No goal calculated"
            }
            
    except Exception as e:
        context = {
            "success": False,
            "error": f"Error calculating goal: {str(e)}"
        }
    
    return render(request, "fitbit/popup_result.html", context)
    
def send_weekly_message(request, participant_id):
    participant = get_object_or_404(Participant, id=participant_id)
    
    # First calculate the weekly goal
    goal_data = run_weekly_algorithm(participant)
    
    if goal_data:
        # Send notification (prints message and saves to message_history)
        if send_goal_notification(participant, goal_data):
            messages.success(request, f"Weekly message created for {participant.user.email}")
        else:
            messages.error(request, f"Failed to create message for {participant.user.email}")
    else:
        messages.warning(request, f"No goal data available for {participant.user.email}")
    
    return redirect('/admin/core/customuser/')
    