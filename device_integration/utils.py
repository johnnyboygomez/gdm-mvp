# device_integration/utils.py

import requests
from datetime import timedelta
from django.shortcuts import get_object_or_404
from core.models import Participant, DeviceAccount

def fetch_fitbit_data_for_participant(participant_id):
    participant = get_object_or_404(Participant, pk=participant_id)
    access_token = participant.fitbit_access_token
    if not access_token:
        return {"error": "No Fitbit access token found"}, 400

    start_date = participant.start_date
    end_date = start_date + timedelta(days=1095)
    url = f"https://api.fitbit.com/1/user/-/activities/steps/date/{start_date}/{end_date}.json"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        return {"error": response.text}, response.status_code

    participant.daily_steps = response.json().get("activities-steps", [])
    participant.save()
    return participant.daily_steps, 200


def add_device_account_for_participant(participant, device_type):
    if DeviceAccount.objects.filter(participant=participant, device_type=device_type).exists():
        return None, f"{device_type} account already exists for this participant."

    device = DeviceAccount(participant=participant, device_type=device_type)
    device.save()
    return device, None
