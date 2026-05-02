Gmail OAuth (optional)
----------------------
1. In Google Cloud Console: enable Gmail API, create OAuth Web client, download JSON.

2. Save your download AS this exact filename (do not commit to git):
   credentials/google_oauth_credentials.json

3. OAuth consent screen: add your Gmail as a "Test user" while the app is in Testing.

4. If your client secret was ever pasted in chat or committed to GitHub, create a new
   secret in Google Cloud (Credentials > your OAuth client > Reset secret).

Environment overrides:
  GOOGLE_OAUTH_CLIENT_SECRETS  path to JSON (default: credentials/google_oauth_credentials.json)
  GOOGLE_REDIRECT_URI          must match the JSON redirect_uris (default: http://127.0.0.1:5000/oauth2callback)
  FLASK_SECRET_KEY             set in production for stable sessions

Local HTTP: OAUTHLIB_INSECURE_TRANSPORT=1 is set automatically unless FLASK_ENV=production.

If you see "Missing code verifier": restart the app after updating — SpamSense stores PKCE in the session between /auth/google and /oauth2callback.
