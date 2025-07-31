from django.shortcuts import redirect
from django.http import HttpResponse, JsonResponse
from django.conf import settings
import os
import urllib.parse
import base64
import requests

def index(request):
    return HttpResponse("Fitbit integration homepage")

def authorize_fitbit(request):
    client_id = os.environ.get('FITBIT_CLIENT_ID')
    redirect_uri = settings.FITBIT_REDIRECT_URI

    scope = "activity heartrate location nutrition profile settings sleep social weight"

    auth_url = (
        "https://www.fitbit.com/oauth2/authorize?"
        + urllib.parse.urlencode({
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scope,
        })
    )

    return redirect(auth_url)

def fitbit_callback(request):
    code = request.GET.get('code')
    if not code:
        return JsonResponse({"error": "No code parameter in callback"})

    client_id = os.environ.get('FITBIT_CLIENT_ID')
    client_secret = os.environ.get('FITBIT_CLIENT_SECRET')
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
    return JsonResponse(response.json())
