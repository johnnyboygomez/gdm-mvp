# core/forms.py

from django import forms
from core.models import DeviceAccount

class AddDeviceForm(forms.ModelForm):
    DEVICE_CHOICES = [
        ('fitbit', 'Fitbit'),
        ('garmin', 'Garmin'),
    ]
    device_type = forms.ChoiceField(choices=DEVICE_CHOICES)

    class Meta:
        model = DeviceAccount
        fields = ('device_type',)
