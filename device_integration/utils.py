# device_integration/utils.py

import requests
from datetime import timedelta
from django.shortcuts import get_object_or_404
from core.models import Participant


def add_device_account_for_participant(participant, device_type):
    if DeviceAccount.objects.filter(participant=participant, device_type=device_type).exists():
        return None, f"{device_type} account already exists for this participant."

    device = DeviceAccount(participant=participant, device_type=device_type)
    device.save()
    return device, None
