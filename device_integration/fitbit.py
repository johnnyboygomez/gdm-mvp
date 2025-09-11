# device_integration/fitbit.py

import requests
import logging
import base64
import uuid
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from django.shortcuts import get_object_or_404
from core.models import Participant

###############
# State / token helpers
def refresh_fitbit_tokens(participant):
    # Check if token is still valid
    if participant.fitbit_token_expires and participant.fitbit_token_expires > timezone.now():
        return participant.fitbit_access_token

    # Prepare Fitbit token refresh request
    token_url = "https://api.fitbit.com/oauth2/token"
    client_id = settings.FITBIT_CLIENT_ID
    client_secret = settings.FITBIT_CLIENT_SECRET

    credentials = f"{client_id}:{client_secret}"
    basic_auth = base64.b64encode(credentials.encode()).decode()
    headers = {
        "Authorization": f"Basic {basic_auth}",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    data = {
        "grant_type": "refresh_token",
        "refresh_token": participant.fitbit_refresh_token,
    }

    # Send request to Fitbit
    resp = requests.post(token_url, headers=headers, data=data)
    if resp.status_code != 200:
        raise Exception(f"Failed to refresh Fitbit token: {resp.text}")

    # Save new tokens
    tokens = resp.json()
    participant.fitbit_access_token = tokens["access_token"]
    participant.fitbit_refresh_token = tokens["refresh_token"]
    participant.fitbit_token_expires = timezone.now() + timedelta(seconds=tokens["expires_in"])
    participant.save(update_fields=["fitbit_access_token", "fitbit_refresh_token", "fitbit_token_expires"])

    return participant.fitbit_access_token
 

###############
# Authorization URL
def get_authorize_url(participant):
    client_id = settings.FITBIT_CLIENT_ID
    redirect_uri = settings.FITBIT_REDIRECT_URI
    state = str(participant.fitbit_auth_token)

    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": "activity heartrate profile",
        "state": state,
        "prompt": "login",
    }

    from urllib.parse import urlencode
    return f"https://www.fitbit.com/oauth2/authorize?{urlencode(params)}"

###############
# Exchange code for tokens and save
def exchange_code_for_tokens(code, state):
    try:
        participant = Participant.objects.get(fitbit_auth_token=state)
    except Participant.DoesNotExist:
        return None, "Participant not found"

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
    credentials = f"{client_id}:{client_secret}"
    basic_auth = base64.b64encode(credentials.encode()).decode()
    headers = {
        "Authorization": f"Basic {basic_auth}",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    resp = requests.post(token_url, data=data, headers=headers)
    if resp.status_code != 200:
        return None, f"Token exchange failed: {resp.text}"

    tokens = resp.json()
    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")
    expires_in = tokens.get("expires_in")

    # Fetch Fitbit profile to get user_id
    profile_resp = requests.get(
        "https://api.fitbit.com/1/user/-/profile.json",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    if profile_resp.status_code != 200:
        return None, f"Failed to fetch profile: {profile_resp.text}"

    profile_data = profile_resp.json()
    fitbit_user_id = profile_data.get("user", {}).get("encodedId")

    participant.fitbit_access_token = access_token
    participant.fitbit_refresh_token = refresh_token
    participant.fitbit_user_id = fitbit_user_id
    if expires_in:
        participant.fitbit_token_expires = datetime.utcnow() + timedelta(seconds=expires_in)
    participant.save()
    return participant, None

###############
# Fetch Fitbit steps

def fetch_fitbit_data_for_participant(participant_id):
    print(f"--- Starting fetch for participant {participant_id} ---")
    
    try: 
        participant = get_object_or_404(Participant, pk=participant_id)
        if not participant.fitbit_access_token:
            return {"error": "No Fitbit access token found"}, 400
        
        print(f"Found participant: {participant}")

        # Refresh token if needed
        if participant.fitbit_token_expires and participant.fitbit_token_expires > timezone.now():
            access_token = participant.fitbit_access_token
            print(f"Access token still valid: {access_token[:10]}... (truncated)")
        else:
            print("Access token expired, refreshing...")
            try:
                access_token = refresh_fitbit_tokens(participant)
                print(f"New access token obtained: {access_token[:10]}... (truncated)")
            except Exception as e:
                print(f"Error refreshing token: {e}")
                return {"error": str(e)}, 400

        # Fetch steps
        start_date = participant.start_date
        end_date = start_date + timedelta(days=1095)
        url = f"https://api.fitbit.com/1/user/-/activities/steps/date/{start_date}/{end_date}.json"
        headers = {"Authorization": f"Bearer {access_token}"}
        print(f"Fetching Fitbit data from: {url}")

        resp = requests.get(url, headers=headers)
        if resp.status_code != 200:
            print(f"Fitbit API returned error {resp.status_code}: {resp.text}")
            return {"error": resp.text}, resp.status_code

        steps = resp.json().get("activities-steps", [])
        filtered_steps = [day for day in steps if int(day.get("value", 0)) > 0]  # filter out zero values
        print(f"Fetched {len(filtered_steps)} days of steps (non-zero only)")

        participant.daily_steps = filtered_steps
        participant.save(update_fields=["daily_steps"])
        print("Participant.daily_steps updated successfully.")

        return {"steps": filtered_steps}, 200

    except requests.RequestException as e:
        logging.error(f"Fitbit API request failed: {e}")
        return {"error": "Failed to fetch data from Fitbit"}, 500
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return {"error": "Internal server error"}, 500


###############
# Add a device account
def add_device_account_for_participant(participant, device_type):
    from core.models import DeviceAccount

    if DeviceAccount.objects.filter(participant=participant, device_type=device_type).exists():
        return None, f"{device_type} account already exists for this participant."

    device = DeviceAccount(participant=participant, device_type=device_type)
    device.save()
    return device, None
