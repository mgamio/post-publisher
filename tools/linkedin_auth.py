"""Gets a LinkedIn access token for posting on your profile (valid 60 days).

Usage (run on your own computer, it opens the browser):
    python tools/linkedin_auth.py <client id> <client secret>

The LinkedIn app needs the products "Share on LinkedIn" and "Sign In with LinkedIn
using OpenID Connect", and http://localhost:8765/callback as an authorized redirect URL.
"""
import secrets
import sys
import webbrowser
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlsplit

import requests

try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

REDIRECT_URI = "http://localhost:8765/callback"
SCOPES = "openid profile w_member_social"


def wait_for_code(state):
    result = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            query = parse_qs(urlsplit(self.path).query)
            if query.get("state", [""])[0] != state:
                result["error"] = "state mismatch"
            elif "code" in query:
                result["code"] = query["code"][0]
            else:
                result["error"] = query.get("error_description", query.get("error", ["unknown"]))[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Done, you can close this tab and go back to the terminal.")

        def log_message(self, *args):
            pass

    server = HTTPServer(("localhost", 8765), Handler)
    while not result:
        server.handle_request()
    if "error" in result:
        sys.exit(f"LinkedIn login failed: {result['error']}")
    return result["code"]


def main(client_id, client_secret):
    state = secrets.token_urlsafe(16)
    url = "https://www.linkedin.com/oauth/v2/authorization?" + urlencode({
        "response_type": "code", "client_id": client_id, "redirect_uri": REDIRECT_URI,
        "scope": SCOPES, "state": state,
    })
    print("Opening the browser to log in to LinkedIn. If it does not open, visit:\n" + url)
    webbrowser.open(url)
    code = wait_for_code(state)

    token = requests.post("https://www.linkedin.com/oauth/v2/accessToken", data={
        "grant_type": "authorization_code", "code": code, "redirect_uri": REDIRECT_URI,
        "client_id": client_id, "client_secret": client_secret,
    }, timeout=30)
    token.raise_for_status()
    token = token.json()
    me = requests.get("https://api.linkedin.com/v2/userinfo", timeout=30,
                      headers={"Authorization": f"Bearer {token['access_token']}"})
    me.raise_for_status()

    expires = date.today() + timedelta(seconds=token["expires_in"])
    print("\nAdd/update these GitHub secrets (Settings > Secrets and variables > Actions):\n")
    print(f"LINKEDIN_ACCESS_TOKEN   = {token['access_token']}")
    print(f"LINKEDIN_AUTHOR         = urn:li:person:{me.json()['sub']}")
    print(f"LINKEDIN_TOKEN_EXPIRES  = {expires.isoformat()}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
