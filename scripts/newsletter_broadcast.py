#!/usr/bin/env python3
"""
Newsletter Broadcaster + Subscriber Limit Notifier
Triggered by GitHub Actions on push to newsletter/posts/*.md

Flow:
1. Detect new/changed .md post in newsletter/posts/
2. Convert Markdown -> HTML
3. Create & send campaign via MailerLite API v2
4. Check subscriber count — if >= NOTIFY_THRESHOLD, send warning email
"""

import os
import sys
import json
import subprocess
import requests
import markdown
from datetime import datetime

# ── Config from env ──────────────────────────────────────────────────────────
API_TOKEN        = os.environ['MAILERLITE_API_TOKEN']
GROUP_ID         = os.environ['MAILERLITE_GROUP_ID']
NOTIFY_EMAIL     = os.environ['NOTIFY_EMAIL']
SUBSCRIBER_LIMIT = int(os.environ.get('SUBSCRIBER_LIMIT', '1000'))
NOTIFY_THRESHOLD = int(os.environ.get('NOTIFY_THRESHOLD', '900'))
MANUAL_SUBJECT   = os.environ.get('MANUAL_SUBJECT', '').strip()

HEADERS = {
    'Authorization': f'Bearer {API_TOKEN}',
    'Content-Type': 'application/json',
    'Accept': 'application/json',
}
BASE = 'https://connect.mailerlite.com/api'


def get_changed_posts():
    """Return list of .md files changed in this push."""
    result = subprocess.run(
        ['git', 'diff', '--name-only', 'HEAD~1', 'HEAD'],
        capture_output=True, text=True
    )
    files = result.stdout.strip().splitlines()
    posts = [f for f in files if f.startswith('newsletter/posts/') and f.endswith('.md')]
    return posts


def parse_post(filepath):
    """Parse frontmatter + body from a .md file."""
    with open(filepath, 'r', encoding='utf-8') as fh:
        raw = fh.read()

    subject = MANUAL_SUBJECT
    body_md = raw

    # Simple frontmatter parser (--- key: value ---)
    if raw.startswith('---'):
        parts = raw.split('---', 2)
        if len(parts) >= 3:
            fm_lines = parts[1].strip().splitlines()
            for line in fm_lines:
                if ':' in line:
                    k, v = line.split(':', 1)
                    if k.strip().lower() == 'subject':
                        subject = v.strip()
            body_md = parts[2].strip()

    if not subject:
        # Fallback: use first H1 heading
        for line in body_md.splitlines():
            if line.startswith('# '):
                subject = line[2:].strip()
                break
    if not subject:
        subject = f'New update from Zakiul Fahmi Jailani — {datetime.now().strftime("%B %Y")}'

    html_body = markdown.markdown(body_md, extensions=['extra', 'nl2br'])
    return subject, html_body


def wrap_html(subject, content_html):
    """Wrap content in a styled email template."""
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  body {{ font-family: 'Georgia', serif; background: #f5f2ee; margin: 0; padding: 0; }}
  .wrapper {{ max-width: 600px; margin: 40px auto; background: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 12px rgba(0,0,0,.08); }}
  .header {{ background: #1e1e1c; padding: 32px 40px; }}
  .header h1 {{ color: #CC7D5E; font-size: 18px; margin: 0 0 4px; font-family: 'Georgia', serif; }}
  .header p {{ color: rgba(249,249,247,.5); font-size: 13px; margin: 0; font-family: sans-serif; }}
  .body {{ padding: 36px 40px; color: #2a2520; line-height: 1.75; font-size: 16px; }}
  .body h1, .body h2, .body h3 {{ color: #1e1e1c; font-family: 'Georgia', serif; }}
  .body a {{ color: #CC7D5E; }}
  .body img {{ max-width: 100%; border-radius: 6px; }}
  .footer {{ background: #f5f2ee; padding: 24px 40px; text-align: center; font-size: 12px; color: #999; font-family: sans-serif; }}
  .footer a {{ color: #CC7D5E; }}
</style>
</head>
<body>
<div class="wrapper">
  <div class="header">
    <h1>Zakiul Fahmi Jailani</h1>
    <p>GeoAI Researcher &amp; Lecturer · Bakrie University</p>
  </div>
  <div class="body">{content_html}</div>
  <div class="footer">
    You're receiving this because you subscribed at
    <a href="https://zakiulfahmijailani.github.io">zakiulfahmijailani.github.io</a>.<br>
    <a href="{{{{ unsubscribe }}}}">Unsubscribe</a>
  </div>
</div>
</body></html>"""


def create_and_send_campaign(subject, html):
    """Create a campaign and send it immediately."""
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

    # 1. Create campaign
    payload = {
        'name': f'[Auto] {subject} — {now}',
        'type': 'regular',
        'status': 'draft',
        'language_id': 1,
        'emails': [{
            'subject': subject,
            'from_name': 'Zakiul Fahmi Jailani',
            'from': NOTIFY_EMAIL,
            'content': html,
        }],
        'groups': [GROUP_ID],
    }
    r = requests.post(f'{BASE}/campaigns', headers=HEADERS, json=payload)
    r.raise_for_status()
    campaign_id = r.json()['data']['id']
    print(f'✅ Campaign created: {campaign_id}')

    # 2. Schedule immediately
    r2 = requests.post(
        f'{BASE}/campaigns/{campaign_id}/schedule',
        headers=HEADERS,
        json={'delivery': 'instant'}
    )
    r2.raise_for_status()
    print(f'🚀 Campaign scheduled for immediate delivery.')
    return campaign_id


def get_subscriber_count():
    """Return total active subscriber count."""
    r = requests.get(
        f'{BASE}/groups/{GROUP_ID}/subscribers',
        headers=HEADERS,
        params={'limit': 1, 'filter[status]': 'active'}
    )
    r.raise_for_status()
    data = r.json()
    # MailerLite returns total in meta.total
    return data.get('meta', {}).get('total', 0)


def send_limit_warning(count):
    """Send a warning email to the owner using MailerLite transactional or campaign."""
    print(f'⚠️  Subscriber count {count} >= threshold {NOTIFY_THRESHOLD}. Sending warning email...')

    subject = f'⚠️ Newsletter Limit Warning: {count}/{SUBSCRIBER_LIMIT} subscribers'
    html = f"""<html><body style="font-family:sans-serif;padding:32px;color:#2a2520">
<h2 style="color:#CC7D5E">⚠️ Subscriber Limit Warning</h2>
<p>Hi Zaki,</p>
<p>Your newsletter (<strong>Website Subscribers</strong>) has reached
<strong>{count} out of {SUBSCRIBER_LIMIT}</strong> subscribers
({round(count/SUBSCRIBER_LIMIT*100)}% full).</p>
<p>You set a notification threshold of <strong>{NOTIFY_THRESHOLD} subscribers</strong>.</p>
<ul>
  <li>Current subscribers: <strong>{count}</strong></li>
  <li>Limit: <strong>{SUBSCRIBER_LIMIT}</strong></li>
  <li>Remaining capacity: <strong>{SUBSCRIBER_LIMIT - count}</strong></li>
</ul>
<p>Please consider upgrading your MailerLite plan before reaching the limit to avoid
new subscribers being rejected.</p>
<p><a href="https://app.mailerlite.com/billing" style="color:#CC7D5E">→ Review MailerLite billing</a></p>
<hr style="border:1px solid #eee;margin:24px 0">
<p style="color:#999;font-size:12px">This is an automated message from your GitHub Actions newsletter workflow.</p>
</body></html>"""

    # Use MailerLite's email transactional endpoint
    payload = {
        'from': {'email': NOTIFY_EMAIL, 'name': 'Newsletter Bot'},
        'to': [{'email': NOTIFY_EMAIL}],
        'subject': subject,
        'html': html,
    }
    r = requests.post(f'{BASE}/emails', headers=HEADERS, json=payload)
    if r.status_code in (200, 201, 204):
        print(f'📧 Warning email sent to {NOTIFY_EMAIL}')
    else:
        print(f'⚠️  Could not send warning via transactional email (status {r.status_code}): {r.text}')
        print('   (Warning was logged above — check your subscriber count manually.)')


def main():
    posts = get_changed_posts()

    if not posts:
        print('ℹ️  No new newsletter posts detected in this push. Skipping broadcast.')
        print('   Running subscriber count check only...')
    else:
        for post_path in posts:
            print(f'📝 Processing: {post_path}')
            subject, content_html = parse_post(post_path)
            full_html = wrap_html(subject, content_html)
            create_and_send_campaign(subject, full_html)

    # Always check subscriber count
    count = get_subscriber_count()
    print(f'👥 Active subscribers: {count}/{SUBSCRIBER_LIMIT}')

    if count >= NOTIFY_THRESHOLD:
        send_limit_warning(count)
    else:
        remaining = NOTIFY_THRESHOLD - count
        print(f'✅ Subscriber count OK. Notification will trigger at {NOTIFY_THRESHOLD} ({remaining} more to go).')


if __name__ == '__main__':
    main()
