#!/usr/bin/env python3
"""
Newsletter automation script for zakiulfahmijailani.github.io

Does two things:
  1. Checks subscriber count — if >= SUBSCRIBER_LIMIT_WARN, sends
     a warning email to NOTIFY_EMAIL via Buttondown transactional API.
  2. Reads the latest file in newsletter/ folder and broadcasts it
     as a new email to all subscribers.

Environment variables (set as GitHub Actions secrets):
  BUTTONDOWN_API_KEY    — Buttondown API key
  NOTIFY_EMAIL          — your email to receive warnings
  SUBSCRIBER_LIMIT_WARN — integer threshold (default: 80)
"""

import os
import sys
import json
import glob
import requests
from pathlib import Path

API_KEY   = os.environ["BUTTONDOWN_API_KEY"]
BASE_URL  = "https://api.buttondown.email/v1"
HEADERS   = {
    "Authorization": f"Token {API_KEY}",
    "Content-Type": "application/json",
}
NOTIFY_EMAIL  = os.environ.get("NOTIFY_EMAIL", "")
WARN_LIMIT    = int(os.environ.get("SUBSCRIBER_LIMIT_WARN", "80"))
FREE_MAX      = 100  # Buttondown free tier hard limit


def get_subscriber_count() -> int:
    """Return total confirmed subscriber count."""
    r = requests.get(
        f"{BASE_URL}/subscribers",
        headers=HEADERS,
        params={"type": "regular", "page": 1},
        timeout=15,
    )
    r.raise_for_status()
    data = r.json()
    return data.get("count", 0)


def send_warning_email(count: int) -> None:
    """Send a warning to NOTIFY_EMAIL that subscriber limit is approaching."""
    if not NOTIFY_EMAIL:
        print("[warn] NOTIFY_EMAIL not set — skipping warning email.")
        return

    subject = f"\u26a0\ufe0f Buttondown: {count}/{FREE_MAX} subscribers — approaching free tier limit"
    body = (
        f"Hi Zaki,\n\n"
        f"Your Buttondown newsletter now has {count} subscribers out of "
        f"{FREE_MAX} allowed on the free tier.\n\n"
        f"You set an alert threshold of {WARN_LIMIT}. "
        f"Please consider upgrading your Buttondown plan at https://buttondown.com/pricing "
        f"before you hit the {FREE_MAX}-subscriber cap.\n\n"
        f"\u2014 GitHub Actions (zakiulfahmijailani.github.io)"
    )

    # Use Buttondown transactional emails endpoint
    payload = {
        "subject": subject,
        "body": body,
        "recipient": NOTIFY_EMAIL,
    }
    r = requests.post(
        f"{BASE_URL}/emails",
        headers=HEADERS,
        json=payload,
        timeout=15,
    )
    if r.status_code in (200, 201):
        print(f"[ok] Warning email sent to {NOTIFY_EMAIL}")
    else:
        print(f"[error] Warning email failed: {r.status_code} {r.text}")


def get_latest_newsletter_file() -> Path | None:
    """Find the most recently modified .md or .txt file in newsletter/ folder."""
    files = sorted(
        glob.glob("newsletter/*.md") + glob.glob("newsletter/*.txt"),
        key=os.path.getmtime,
        reverse=True,
    )
    return Path(files[0]) if files else None


def parse_newsletter_file(path: Path) -> tuple[str, str]:
    """
    Parse newsletter file.
    Format expected:
      Line 1:  Subject: <email subject here>
      Line 2+: <email body in Markdown>
    """
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    subject = "New post from Zakiul Fahmi Jailani"
    body_start = 0
    if lines and lines[0].lower().startswith("subject:"):
        subject = lines[0].split(":", 1)[1].strip()
        body_start = 1
    body = "\n".join(lines[body_start:]).strip()
    return subject, body


def broadcast_email(subject: str, body: str) -> None:
    """Send a broadcast email to all subscribers."""
    payload = {
        "subject": subject,
        "body": body,
        "status": "about_to_send",  # queues for immediate sending
    }
    r = requests.post(
        f"{BASE_URL}/emails",
        headers=HEADERS,
        json=payload,
        timeout=15,
    )
    if r.status_code in (200, 201):
        print(f"[ok] Broadcast queued: '{subject}'")
    else:
        print(f"[error] Broadcast failed: {r.status_code} {r.text}")
        sys.exit(1)


if __name__ == "__main__":
    # ── Step 1: Check subscriber count ──────────────────────────────────────
    try:
        count = get_subscriber_count()
        print(f"[info] Current subscribers: {count}/{FREE_MAX}")
    except Exception as e:
        print(f"[error] Could not fetch subscriber count: {e}")
        count = 0

    if count >= WARN_LIMIT:
        print(f"[warn] Subscriber count {count} >= threshold {WARN_LIMIT} — sending warning.")
        send_warning_email(count)
    else:
        print(f"[info] Subscriber count ({count}) is below warning threshold ({WARN_LIMIT}). All good.")

    # ── Step 2: Broadcast latest newsletter file ─────────────────────────────
    newsletter_file = get_latest_newsletter_file()
    if newsletter_file is None:
        print("[info] No newsletter file found in newsletter/ — skipping broadcast.")
        sys.exit(0)

    subject, body = parse_newsletter_file(newsletter_file)
    print(f"[info] Broadcasting: '{subject}' from {newsletter_file}")
    broadcast_email(subject, body)
