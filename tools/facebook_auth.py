"""Gets a Facebook Page access token that does not expire.

Usage (run on your own computer):
    python tools/facebook_auth.py

It asks for the app id, the app secret and a short-lived user token from the Graph API
Explorer (https://developers.facebook.com/tools/explorer/) with the permissions
pages_show_list, pages_read_engagement and pages_manage_posts. The secret and tokens are
typed hidden, so they do not end up in the shell history.
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
    app_id = input("App ID: ").strip()
    app_secret = getpass.getpass("App secret (hidden): ").strip()
    short_token = getpass.getpass("User token from the Graph API Explorer (hidden): ").strip()

    # a page token obtained with a long-lived user token never expires
    long_token = get("oauth/access_token", grant_type="fb_exchange_token", client_id=app_id,
                     client_secret=app_secret, fb_exchange_token=short_token)["access_token"]
    pages = get("me/accounts", fields="id,name,access_token,tasks", access_token=long_token)["data"]
    pages = [p for p in pages if "CREATE_CONTENT" in p.get("tasks", [])]
    if not pages:
        sys.exit("No page you can post on; check the token has pages_show_list and pages_manage_posts")

    for i, page in enumerate(pages, 1):
        print(f"{i}. {page['name']} ({page['id']})")
    page = pages[int(input("Page number: ") if len(pages) > 1 else 1) - 1]

    print("\nAdd these as GitHub secrets (Settings > Secrets and variables > Actions):\n")
    print(f"FACEBOOK_PAGE_ID={page['id']}")
    print(f"FACEBOOK_PAGE_TOKEN={page['access_token']}")


if __name__ == "__main__":
    main()
