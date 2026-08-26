import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


def _send_email(recipient, subject, text):
    api_key = os.getenv("RESEND_API_KEY", "").strip()
    sender = os.getenv("MAIL_FROM", "").strip()
    if not api_key or not sender:
        raise RuntimeError("Email is not configured: RESEND_API_KEY and MAIL_FROM are required.")
    payload = json.dumps({"from": sender, "to": [recipient], "subject": subject, "text": text}).encode("utf-8")
    request = Request("https://api.resend.com/emails", data=payload, headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", "User-Agent": "nafiz-ahmed12s-mail/1.1"}, method="POST")
    try:
        with urlopen(request, timeout=20) as response:
            body = response.read().decode("utf-8", errors="replace")
            if response.status < 200 or response.status >= 300:
                raise RuntimeError(f"Resend returned HTTP {response.status}: {body[:500]}")
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Resend returned HTTP {exc.code}: {body[:500]}") from exc
    except URLError as exc:
        raise RuntimeError(f"Could not reach Resend API: {exc.reason}") from exc


def _base_url():
    base_url = os.getenv("APP_BASE_URL", "").strip().rstrip("/")
    if not base_url:
        raise RuntimeError("Password reset email is not configured: APP_BASE_URL is required.")
    return base_url


def send_password_reset_email(recipient, token):
    reset_url = f"{_base_url()}/reset-password?token={quote(token, safe='')}"
    _send_email(recipient, "Reset your Nafiz Ahmed password", f"We received a request to reset your password.\n\nReset your password: {reset_url}\n\nThis link expires in 30 minutes and can be used only once. If you did not request this, you can safely ignore this email.\n")


def send_admin_password_reset_email(recipient, token):
    reset_url = f"{_base_url()}/admin-reset-password?token={quote(token, safe='')}"
    _send_email(recipient, "Reset your Nafiz Ahmed admin password", f"A request was made to reset your admin password.\n\nReset your admin password: {reset_url}\n\nThis link expires in 30 minutes and can be used only once. If you did not request this, contact the site owner immediately.\n")
