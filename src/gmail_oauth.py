import json
import os

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

DEFAULT_SECRETS_PATH = os.path.join('credentials', 'google_oauth_credentials.json')

def get_client_secrets_path():
    return os.environ.get('GOOGLE_OAUTH_CLIENT_SECRETS', DEFAULT_SECRETS_PATH)

def get_redirect_uri():
    return os.environ.get(
        'GOOGLE_REDIRECT_URI',
        'http://127.0.0.1:5000/oauth2callback',
    )

def secrets_file_exists():
    return os.path.isfile(get_client_secrets_path())

def create_flow(state=None):
    path = get_client_secrets_path()
    if not os.path.isfile(path):
        raise FileNotFoundError(f'Missing OAuth client JSON: {path}')
    kwargs = {
        'client_secrets_file': path,
        'scopes': GMAIL_SCOPES,
        'redirect_uri': get_redirect_uri(),
    }
    if state is not None:
        kwargs['state'] = state
    return Flow.from_client_secrets_file(**kwargs)

def credentials_from_session(session_dict):
    if not session_dict:
        return None
    if isinstance(session_dict, str):
        session_dict = json.loads(session_dict)
    try:
        return Credentials.from_authorized_user_info(session_dict, GMAIL_SCOPES)
    except (ValueError, KeyError, TypeError):
        return None

def credentials_to_session_dict(creds: Credentials):
    return json.loads(creds.to_json())

def build_gmail_service(creds: Credentials):
    return build('gmail', 'v1', credentials=creds, cache_discovery=False)

def get_profile_email(service):
    prof = service.users().getProfile(userId='me').execute()
    return prof.get('emailAddress', '')
