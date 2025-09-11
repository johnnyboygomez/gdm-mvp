# gdm/views.py

from django.shortcuts import render, get_object_or_404
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from django.core import signing
from django.http import JsonResponse
from core.models import Participant
from django.conf import settings
from google.auth.transport import requests as google_requests
from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token as google_id_token
from django.contrib import messages


OAUTH_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]

def _build_redirect_uri(request):
    # Ensures exact match with what you register in Google Console
    return request.build_absolute_uri(reverse('google_oauth_callback'))

def google_oauth_start(request, participant_id: int):
    """Kick off the server-side OAuth flow (Auth Code)."""
    participant = get_object_or_404(Participant, pk=participant_id)

    # Sign state so we can safely round-trip participant identification
    state_payload = {"pid": participant_id}
    state = signing.dumps(state_payload)

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=OAUTH_SCOPES,
        redirect_uri=_build_redirect_uri(request),
    )

    auth_url, flow_state = flow.authorization_url(
        access_type="offline",              # get refresh_token if/when needed
        include_granted_scopes="true",
        prompt="consent select_account",            # always let RA pick account
        state=state,                        # our signed participant state
    )

    # Store Google’s internal state to satisfy library checks on callback
    request.session['google_oauthlib_state'] = flow_state
    return redirect(auth_url)
def google_oauth_callback(request):
    """Handle Google's redirect, exchange code → tokens, save to participant."""
    # ... existing code above ...

    # Persist the essentials you want to track
    participant.google_id = idinfo.get("sub")
    participant.google_email = idinfo.get("email")
    participant.google_access_token = creds.token
    participant.google_refresh_token = creds.refresh_token  # may be None on re-consent
    participant.google_token_expiry = creds.expiry
    participant.save()

    '''
    # return full credentials and idinfo as JSON ---- for debugging
    return JsonResponse({
        "credentials": {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "id_token": creds.id_token,
            "scopes": creds.scopes,
            "expiry": creds.expiry.isoformat() if creds.expiry else None,
        },
        "idinfo": idinfo,
    })
    '''

    # Simple confirmation; you can redirect back to the admin change page if you prefer
    messages.success(request, "Google authorization successful.")
    return redirect(reverse('admin:auth_user_change', args=[participant.user_id]))
