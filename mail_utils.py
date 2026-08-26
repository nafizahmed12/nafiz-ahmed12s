import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


RESEND_API_URL = "https://api.resend.com/emails"


def _required_env(name):
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Email is not configured: {name} is missing.")
    return value


def _send_email(recipient, subject, text):
    api_key = _required_env("RESEND_API_KEY")
    sender = _required_env("MAIL_FROM")
    recipient = (recipient or "").strip().lower()
    if not recipient:
        raise RuntimeError("Cannot send email: recipient address is empty.")

    payload_data = {
        "from": sender,
        "to": [recipient],
        "subject": subject,
        "text": text,
    }
    reply_to = os.getenv("MAIL_REPLY_TO", "").strip()
    if reply_to:
        payload_data["reply_to"] = reply_to

    payload = json.dumps(payload_data).encode("utf-8")
    request = Request(
        RESEND_API_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "nafiz-ahmed12s-mail/1.2",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=20) as response:
            body = response.read().decode("utf-8", errors="replace")
            if response.status < 200 or response.status >= 300:
                raise RuntimeError(f"Resend returned HTTP {response.status}: {body[:1000]}")
            try:
                result = json.loads(body) if body else {}
            except json.JSONDecodeError:
                result = {}
            message_id = result.get("id")
            if not message_id:
                raise RuntimeError(f"Resend accepted an unexpected response: {body[:1000]}")
            return message_id
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Resend returned HTTP {exc.code}: {body[:1000]}") from exc
    except URLError as exc:
        raise RuntimeError(f"Could not reach Resend API: {exc.reason}") from exc


def _base_url():
    base_url = os.getenv("APP_BASE_URL", "").strip().rstrip("/")
    if not base_url:
        base_url = os.getenv("RENDER_EXTERNAL_URL", "").strip().rstrip("/")
    if not base_url:
        raise RuntimeError("Password reset email is not configured: APP_BASE_URL is required.")
    return base_url


def send_password_reset_email(recipient, token):
    reset_url = f"{_base_url()}/reset-password?token={quote(token, safe='')}"
    return _send_email(
        recipient,
        "Reset your Nafiz Ahmed password",
        f"We received a request to reset your password.\n\nReset your password: {reset_url}\n\nThis link expires in 30 minutes and can be used only once. If you did not request this, you can safely ignore this email.\n",
    )


def build_admin_reset_url(token):
    return f"{_base_url()}/admin-reset-password?token={quote(token, safe='')}"


def send_admin_password_reset_email(recipient, token):
    reset_url = build_admin_reset_url(token)
    return _send_email(
        recipient,
        "Reset your Nafiz Ahmed admin password",
        f"A request was made to reset your admin password.\n\nReset your admin password: {reset_url}\n\nThis link expires in 30 minutes and can be used only once. If you did not request this, contact the site owner immediately.\n",
    )
