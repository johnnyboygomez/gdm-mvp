# goals/views.py
from django.shortcuts import render, get_object_or_404
from core.models import Participant
from .targets import run_weekly_algorithm

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