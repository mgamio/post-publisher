"""Gets a Facebook Page access token that does not expire.

Usage (run on your own computer):
    python tools/facebook_auth.py

First get a user token in the Graph API Explorer (https://developers.facebook.com/tools/explorer/)
with the permissions pages_show_list, pages_read_engagement and pages_manage_posts. Then either
  - extend it yourself: Access Token Debugger > "Extend Access Token", and leave the App ID
    empty when asked (no app secret needed), or
  - give the App ID and app secret, and this script extends it.
Secrets and tokens are typed hidden, so they do not end up in the shell history.
"""
import getpass
import sys

import requests

try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

GRAPH = "https://graph.facebook.com/v26.0"


def get(path, **params):
    resp = requests.get(f"{GRAPH}/{path}", params=params, timeout=30)
    if not resp.ok:
        sys.exit(f"Facebook returned {resp.status_code}: {resp.text[:300]}")
    return resp.json()


def main():
    app_id = input("App ID (leave empty if you already extended the token): ").strip()
    if app_id:
        app_secret = getpass.getpass("App secret (hidden): ").strip()
        # an app secret is 32 hex characters; anything else is a copy/paste problem
        if len(app_secret) != 32 or any(c not in "0123456789abcdef" for c in app_secret.lower()):
            sys.exit(f"The app secret should be 32 characters (0-9, a-f), got {len(app_secret)}. "
                     "Copy it again from App settings > Basic > App secret > Show.")
    user_token = getpass.getpass("User token (hidden): ").strip()

    # a page token obtained with a long-lived user token never expires
    if app_id:
        user_token = get("oauth/access_token", grant_type="fb_exchange_token", client_id=app_id,
                         client_secret=app_secret, fb_exchange_token=user_token)["access_token"]
    pages = get("me/accounts", fields="id,name,access_token,tasks", access_token=user_token)["data"]
    pages = [p for p in pages if "CREATE_CONTENT" in p.get("tasks", [])]
    if not pages:
        sys.exit("No page you can post on; check the token has pages_show_list and pages_manage_posts")

    for i, page in enumerate(pages, 1):
        print(f"{i}. {page['name']} ({page['id']})")
    page = pages[int(input("Page number: ") if len(pages) > 1 else 1) - 1]

    info = get("debug_token", input_token=page["access_token"], access_token=page["access_token"])["data"]
    if info.get("expires_at"):
        print("\nWarning: this page token expires; the user token was not a long-lived one. "
              "Extend it in the Access Token Debugger and run this again.")

    print("\nAdd these as GitHub secrets (Settings > Secrets and variables > Actions):\n")
    print(f"FACEBOOK_PAGE_ID={page['id']}")
    print(f"FACEBOOK_PAGE_TOKEN={page['access_token']}")


if __name__ == "__main__":
    main()
