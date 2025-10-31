# device_integration/fitbit.py

import requests
import logging
import base64
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from django.shortcuts import get_object_or_404
from core.models import Participant

###############
# Helpers
def _log_status_flag(participant, key, error_message=None):
    """Helper to set or clear status flags for Fitbit operations."""
    # Get a mutable copy of status_flags to ensure Django detects the change
    flags = participant.status_flags.copy() if participant.status_flags else {}
    
    if error_message:
        flags[key] = True
        flags[f"{key}_last_error"] = error_message
        flags[f"{key}_last_error_time"] = timezone.now().isoformat()
    else:
        flags[key] = False
        flags.pop(f"{key}_last_error", None)
        flags.pop(f"{key}_last_error_time", None)
    
    # Reassign to trigger JSONField update detection
    participant.status_flags = flags
    participant.save(update_fields=["status_flags"])

###############
# Token helpers
def refresh_fitbit_tokens(participant):
    """Refresh Fitbit OAuth2 tokens if expired."""
    if participant.fitbit_token_expires and participant.fitbit_token_expires > timezone.now():
        return participant.fitbit_access_token

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

    resp = requests.post(token_url, headers=headers, data=data)
    if resp.status_code != 200:
        error_msg = f"Failed to refresh Fitbit token: {resp.text}"
        _log_status_flag(participant, "refresh_fitbit_token_fail", error_msg)
        raise Exception(error_msg)

    # SUCCESS - clear previous errors
    _log_status_flag(participant, "refresh_fitbit_token_fail")

    tokens = resp.json()
    participant.fitbit_access_token = tokens["access_token"]
    participant.fitbit_refresh_token = tokens["refresh_token"]
    participant.fitbit_token_expires = timezone.now() + timedelta(seconds=tokens["expires_in"])
    participant.save(update_fields=["fitbit_access_token", "fitbit_refresh_token", "fitbit_token_expires", "status_flags"])
    return participant.fitbit_access_token

###############
# Authorization URL
def get_authorize_url(participant):
    from urllib.parse import urlencode
    params = {
        "response_type": "code",
        "client_id": settings.FITBIT_CLIENT_ID,
        "redirect_uri": settings.FITBIT_REDIRECT_URI,
        "scope": "activity heartrate profile",
        "state": str(participant.fitbit_auth_token),
        "prompt": "login",
    }
    return f"https://www.fitbit.com/oauth2/authorize?{urlencode(params)}"

###############
# Exchange code for tokens
def exchange_code_for_tokens(code, state):
    try:
        participant = Participant.objects.get(fitbit_auth_token=state)
    except Participant.DoesNotExist:
        return None, "Participant not found"

    token_url = "https://api.fitbit.com/oauth2/token"
    data = {
        "client_id": settings.FITBIT_CLIENT_ID,
        "grant_type": "authorization_code",
        "redirect_uri": settings.FITBIT_REDIRECT_URI,
        "code": code,
    }
    credentials = f"{settings.FITBIT_CLIENT_ID}:{settings.FITBIT_CLIENT_SECRET}"
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

    # Fetch Fitbit profile
    profile_resp = requests.get(
        "https://api.fitbit.com/1/user/-/profile.json",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    if profile_resp.status_code != 200:
        return None, f"Failed to fetch profile: {profile_resp.text}"

    fitbit_user_id = profile_resp.json().get("user", {}).get("encodedId")
    
    # VALIDATE: Compare authenticated ID with pre-entered ID
    if participant.fitbit_user_id and participant.fitbit_user_id != "tempid" and participant.fitbit_user_id != fitbit_user_id:
        return None, (
            f"Wrong Fitbit account! Expected Fitbit User ID: {participant.fitbit_user_id}, "
            f"but authenticated with ID: {fitbit_user_id}. "
            f"Please authenticate with the correct Fitbit account."
        )

    participant.fitbit_access_token = access_token
    participant.fitbit_refresh_token = refresh_token
    participant.fitbit_user_id = fitbit_user_id
    if expires_in:
        participant.fitbit_token_expires = timezone.now() + timedelta(seconds=expires_in)
    
    # Clear all Fitbit-related error flags on successful authentication
    _log_status_flag(participant, "refresh_fitbit_token_fail")
    _log_status_flag(participant, "fetch_fitbit_data_fail")
    
    # Explicitly save the fields we modified
    participant.save(update_fields=[
        "fitbit_access_token", 
        "fitbit_refresh_token", 
        "fitbit_user_id", 
        "fitbit_token_expires"
    ])
    
    return participant, None

###############
# Fetch Fitbit steps (with incremental fetch)
def fetch_fitbit_data_for_participant(participant_id, force_refetch=False):
    participant = get_object_or_404(Participant, pk=participant_id)
    print(f"--- Fetching Fitbit data for participant {participant_id} ---")

    if not participant.fitbit_access_token:
        _log_status_flag(participant, "fetch_fitbit_data_fail", "No Fitbit access token")
        return {"error": "No Fitbit access token"}, 400

    try:
        # Determine start and end date
        daily_steps = participant.daily_steps or []
        if force_refetch or not daily_steps:
            start_fetch_date = participant.start_date - timedelta(days=7)
        else:
            last_date = max(day["date"] for day in daily_steps)
            start_fetch_date = datetime.strptime(last_date, "%Y-%m-%d").date()

        end_fetch_date = min(timezone.now().date(), participant.start_date + timedelta(days=365))
        
        # Clear error flag as soon as we confirm valid token and before any early returns
        # This ensures that if participant was previously in error state, it gets cleared
        # even if no actual fetch is needed (already up to date case)
        _log_status_flag(participant, "fetch_fitbit_data_fail")
        
        if start_fetch_date > end_fetch_date:
            return {"steps": daily_steps, "message": "Already up to date"}, 200

        # Refresh token if needed
        access_token = participant.fitbit_access_token
        if not participant.fitbit_token_expires or participant.fitbit_token_expires <= timezone.now():
            access_token = refresh_fitbit_tokens(participant)

        # Fetch steps from Fitbit API
        url = f"https://api.fitbit.com/1/user/-/activities/steps/date/{start_fetch_date}/{end_fetch_date}.json"
        headers = {"Authorization": f"Bearer {access_token}"}
        resp = requests.get(url, headers=headers)
        if resp.status_code != 200:
            _log_status_flag(participant, "fetch_fitbit_data_fail", f"Fitbit API error {resp.status_code}: {resp.text}")
            return {"error": resp.text}, resp.status_code

        # Process steps
        steps = resp.json().get("activities-steps", [])
        new_steps = [{"date": d["dateTime"], "value": int(d.get("value", 0))} for d in steps if int(d.get("value", 0)) > 0]
        steps_dict = {day["date"]: day for day in daily_steps}
        for day in new_steps:
            steps_dict[day["date"]] = day
        merged_steps = sorted(steps_dict.values(), key=lambda x: x["date"])
        participant.daily_steps = merged_steps
        # Note: Error flag already cleared at top of try block
        participant.save(update_fields=["daily_steps", "status_flags"])
        print(f"Fetched and merged {len(merged_steps)} days of step data.")

        return {"steps": merged_steps}, 200

    except requests.RequestException as e:
        error_msg = f"Fitbit API request failed: {e}"
        logging.error(error_msg)
        _log_status_flag(participant, "fetch_fitbit_data_fail", error_msg)
        return {"error": "Failed to fetch data from Fitbit"}, 500
    except Exception as e:
        error_msg = f"Unexpected error: {e}"
        logging.error(error_msg)
        _log_status_flag(participant, "fetch_fitbit_data_fail", error_msg)
        return {"error": "Internal server error"}, 500

###############
# Add device account
def add_device_account_for_participant(participant, device_type):
    from core.models import DeviceAccount
    if DeviceAccount.objects.filter(participant=participant, device_type=device_type).exists():
        return None, f"{device_type} account already exists for this participant."
    device = DeviceAccount(participant=participant, device_type=device_type)
    device.save()
    return device, None