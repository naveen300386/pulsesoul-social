"""
Threads access tokens die after 60 days. Every other token in this project is
long-lived; this is the one that needs a hand.

    python tools/refresh_threads.py

Reads THREADS_TOKEN from .env (or the environment), asks Threads for a fresh
60-day token, and prints it. Paste the result over the THREADS_TOKEN secret
on GitHub.

You can run this any time after the token is 24 hours old, and it must be run
before day 60.
"""
import os
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]


def load_env() -> None:
    path = ROOT / ".env"
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def main() -> int:
    load_env()
    token = os.environ.get("THREADS_TOKEN", "").strip()
    if not token:
        print("No THREADS_TOKEN found in .env or the environment.")
        print("Put it in .env first, or run:  $env:THREADS_TOKEN='...'  then run this again.")
        return 1

    resp = requests.get(
        "https://graph.threads.net/refresh_access_token",
        params={"grant_type": "th_refresh_token", "access_token": token},
        timeout=60,
    )
    if resp.status_code >= 400:
        print(f"Threads refused the refresh (HTTP {resp.status_code}):\n{resp.text[:500]}")
        print("\nIf it says the token is expired, generate a brand new one:")
        print("  developers.facebook.com -> your app -> Threads API -> Generate access token")
        return 1

    data = resp.json()
    days = int(data.get("expires_in", 0)) // 86400
    print("\nNew Threads token (valid for about %d days):\n" % days)
    print(data["access_token"])
    print("\nPaste that into:")
    print("  GitHub -> your repo -> Settings -> Secrets and variables -> Actions -> THREADS_TOKEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
