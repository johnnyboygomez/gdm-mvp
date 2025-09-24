# device_integration/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from core.models import Participant
from device_integration.fitbit import exchange_code_for_tokens, get_authorize_url, fetch_fitbit_data_for_participant
from django.http import JsonResponse

def fitbit_callback(request):
    code = request.GET.get("code")
    state = request.GET.get("state")

    participant, error = exchange_code_for_tokens(code, state)
    if participant:
        return render(request, "admin/popup_result.html", {
            "success": True,
            "fitbit_id": participant.fitbit_user_id,
        })
    else:
        return render(request, "admin/popup_result.html", {
            "success": False,
            "error": error,
        })

def fitbit_auth_start(request, participant_id):
    participant = get_object_or_404(Participant, pk=participant_id)
    url = get_authorize_url(participant)
    return redirect(url)
    
def fetch_fitbit_data(request, participant_id):
    participant = get_object_or_404(Participant, pk=participant_id)
    result, status = fetch_fitbit_data_for_participant(participant_id)

    if status == 200:
        context = {
            "success": True,
            "fitbit_id": participant.fitbit_user_id,
            "message": f"Fetched {len(result['steps'])} days of steps."
        }
    else:
        context = {
            "success": False,
            "error": result.get("error", "Unknown error")
        }
    return render(request, "admin/popup_result.html", context)