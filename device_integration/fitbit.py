# device_integration/fitbit.py

import requests
import logging
import base64
import time
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from django.shortcuts import get_object_or_404
from core.models import Participant

###############
# Helpers
def _log_status_flag(participant, key, error_message=None):
    """Helper to set or clear status flags for Fitbit operations."""
    if error_message:
        participant.status_flags[key] = True
        participant.status_flags[f"{key}_last_error"] = error_message
        participant.status_flags[f"{key}_last_error_time"] = timezone.now().isoformat()
    else:
        participant.status_flags[key] = False
        participant.status_flags.pop(f"{key}_last_error", None)
        participant.status_flags.pop(f"{key}_last_error_time", None)
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

    participant.fitbit_access_token = access_token
    participant.fitbit_refresh_token = refresh_token
    participant.fitbit_user_id = fitbit_user_id
    if expires_in:
        participant.fitbit_token_expires = timezone.now() + timedelta(seconds=expires_in)
    participant.save()
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
        _log_status_flag(participant, "fetch_fitbit_data_fail")  # clear errors
        participant.save(update_fields=["daily_steps", "status_flags"])
        print(f"Fetched and merged {len(merged_steps)} days of step data.")

        # Estimate wear hours (no circular import - function is in same file)
        estimate_wear_hours(participant.id)

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
# Estimate wear hours
def estimate_wear_hours(participant_id, force_refetch=False):
    """
    Estimate Fitbit wear hours per day using heart rate zones.
    
    REQUIREMENTS:
    - Participant's Fitbit age must be set to 95-99 for this to work
    - With age 95-99, max HR ~120-125 bpm
    - Normal resting HR (60-80 bpm) falls into Fat Burn zone
    - Device not worn = all time in Out of Range zone
    
    METHOD:
    - Fetches heart rate zone data from Fitbit
    - Sums minutes in Fat Burn + Cardio + Peak zones
    - Ignores "Out of Range" zone completely
    - Result = estimated device wear time in hours
    
    Incremental: only fetches days not yet processed.
    """
    participant = get_object_or_404(Participant, pk=participant_id)

    if not participant.fitbit_access_token:
        return {"error": "No Fitbit access token"}, 400

    daily_steps = participant.daily_steps or []
    steps_dict = {day["date"]: day for day in daily_steps}
    
    # Find dates that already have wear_hours
    dates_with_wear_hours = {day["date"] for day in daily_steps if "wear_hours" in day}

    # Determine date range to fetch
    if force_refetch:
        start_fetch_date = participant.start_date
        print("Force refetch: fetching all wear time data from study start")
    elif dates_with_wear_hours:
        last_date = max(dates_with_wear_hours)
        start_fetch_date = datetime.strptime(last_date, "%Y-%m-%d").date()
        print(f"Incremental fetch: starting from {start_fetch_date} (last date with wear_hours, inclusive)")
    else:
        start_fetch_date = participant.start_date
        print("No existing wear time data: fetching from study start")

    end_fetch_date = min(timezone.now().date(), participant.start_date + timedelta(days=365))
    if start_fetch_date > end_fetch_date:
        return {"daily_steps": daily_steps, "message": "Already up to date"}, 200

    access_token = participant.fitbit_access_token
    current_date = start_fetch_date
    estimated_wear_hours = {}

    while current_date <= end_fetch_date:
        date_str = current_date.strftime("%Y-%m-%d")
        url = f"https://api.fitbit.com/1/user/-/activities/heart/date/{date_str}/1d.json"
        headers = {"Authorization": f"Bearer {access_token}"}

        wear_hours = 0
        try:
            resp = requests.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            heart_data = data.get("activities-heart", [])
            
            if heart_data:
                hr_zones = heart_data[0].get("value", {}).get("heartRateZones", [])
                
                # Sum ONLY Fat Burn + Cardio + Peak (ignore "Out of Range")
                wear_minutes = 0
                
                for zone in hr_zones:
                    zone_name = zone.get("name", "")
                    zone_minutes = zone.get("minutes", 0)
                    
                    # Exclude "Out of Range" zone
                    if zone_name != "Out of Range":
                        wear_minutes += zone_minutes
                
                wear_hours = round(wear_minutes / 60, 1)
                
                # Cap at 24 hours
                wear_hours = min(24.0, wear_hours)
                
                print(f"  {date_str}: {wear_hours} hours ({wear_minutes} minutes)")
            else:
                print(f"  {date_str}: No heart rate data")
                
        except requests.RequestException as e:
            error_msg = f"Fitbit heart rate fetch failed for {date_str}: {e}"
            logging.error(error_msg)
            _log_status_flag(participant, "estimate_wear_hours_fail", error_msg)
            current_date += timedelta(days=1)
            continue

        # Store estimate
        estimated_wear_hours[date_str] = wear_hours
        
        # Rate limiting
        time.sleep(1)
        current_date += timedelta(days=1)

    # Merge estimates ONLY into dates that already have step data
    for date_str, hours in estimated_wear_hours.items():
        if date_str in steps_dict:
            steps_dict[date_str]["wear_hours"] = hours

    merged_daily_steps = sorted(steps_dict.values(), key=lambda x: x["date"])
    participant.daily_steps = merged_daily_steps

    # SUCCESS - clear any previous errors
    _log_status_flag(participant, "estimate_wear_hours_fail")
    participant.save(update_fields=["daily_steps", "status_flags"])

    print(f"\nTotal: {len(estimated_wear_hours)} days processed")
    return {"daily_steps": merged_daily_steps}, 200
    
###############
# Add device account
def add_device_account_for_participant(participant, device_type):
    from core.models import DeviceAccount
    if DeviceAccount.objects.filter(participant=participant, device_type=device_type).exists():
        return None, f"{device_type} account already exists for this participant."
    device = DeviceAccount(participant=participant, device_type=device_type)
    device.save()
    return device, None