from django.shortcuts import redirect, get_object_or_404, render
from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from core.models import Participant
import urllib.parse
import os
import base64
import requests
from datetime import datetime, timedelta
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
import uuid
from .utils import regenerate_fitbit_token


@csrf_exempt

def index(request):
    return HttpResponse("Fitbit integration homepage")

def authorize_fitbit(request):
    client_id = settings.FITBIT_CLIENT_ID
    redirect_uri = settings.FITBIT_REDIRECT_URI
    state = request.GET.get("state")
    if not state:
        return HttpResponseBadRequest("Missing state (auth token)")

    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": "activity heartrate profile",
        "state": state,
        "prompt": "login", 
    }

    auth_url = "https://www.fitbit.com/oauth2/authorize?" + urllib.parse.urlencode(params)
    return redirect(auth_url)

def fitbit_callback(request):
    code = request.GET.get('code')
    state = request.GET.get('state')  # This identifies the participant

    if not code or not state:
        return JsonResponse({"error": "Missing code or state"}, status=400)

    try:
        participant = Participant.objects.get(fitbit_auth_token=state)
    except Participant.DoesNotExist:
        return JsonResponse({"error": "Participant not found"}, status=404)

    client_id = settings.FITBIT_CLIENT_ID
    client_secret = settings.FITBIT_CLIENT_SECRET
    redirect_uri = settings.FITBIT_REDIRECT_URI

    token_url = "https://api.fitbit.com/oauth2/token"

    data = {
        "client_id": client_id,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
        "code": code,
    }

    # Base64 encode client_id:client_secret
    credentials = f"{client_id}:{client_secret}"
    basic_auth = base64.b64encode(credentials.encode()).decode()

    headers = {
        "Authorization": f"Basic {basic_auth}",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    response = requests.post(token_url, data=data, headers=headers)

    if response.status_code != 200:
        return JsonResponse({"error": "Token exchange failed", "details": response.text}, status=400)

    token_data = response.json()

    # ---- NEW SECTION: Get Fitbit profile to verify fitbit_user_id ----
    access_token = token_data.get("access_token")
    profile_response = requests.get(
        "https://api.fitbit.com/1/user/-/profile.json",
        headers={"Authorization": f"Bearer {access_token}"}
    )

    if profile_response.status_code != 200:
        return JsonResponse({"error": "Failed to fetch Fitbit profile", "details": profile_response.text}, status=400)

    profile_data = profile_response.json()
    fitbit_user_id = profile_data.get("user", {}).get("encodedId")

    if not fitbit_user_id:
        return JsonResponse({"error": "Could not retrieve Fitbit user_id"}, status=400)
        
    # Save tokens to participant
    participant.fitbit_access_token = token_data.get("access_token")
    participant.fitbit_refresh_token = token_data.get("refresh_token")
    participant.fitbit_user_id = token_data.get("user_id")
    expires_in = token_data.get("expires_in")  # usually seconds
    if expires_in:
        participant.fitbit_token_expires = datetime.utcnow() + timedelta(seconds=expires_in)

    participant.save()
    return JsonResponse({"status": "success", "fitbit_user_id": token_data.get("user_id")})

def participant_detail(request, participant_id):
    participant = get_object_or_404(Participant, pk=participant_id)

    authorize_url = reverse('authorize_fitbit')  # e.g. /fitbit/authorize/
    fitbit_link = f"{authorize_url}?state={participant.fitbit_auth_token}"

    return render(request, 'participants/detail.html', {
        'participant': participant,
        'fitbit_link': fitbit_link,
    })

@login_required
def regenerate_token(request, participant_id):
    try:
        participant = Participant.objects.get(id=participant_id)
        new_token = regenerate_fitbit_token(participant)
        return HttpResponse(f"New token: {new_token}")
    except Participant.DoesNotExist:
        return HttpResponse("Participant not found", status=404)
