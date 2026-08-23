import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


def send_password_reset_email(recipient, token):
    """Send a password-reset email through Resend's HTTPS API.

    HTTPS API delivery is used instead of SMTP because Render Free web services
    can block outbound SMTP ports such as 587.
    """
    api_key = os.getenv("RESEND_API_KEY", "").strip()
    sender = os.getenv("MAIL_FROM", "").strip()
    base_url = os.getenv("APP_BASE_URL", "").strip().rstrip("/")

    if not api_key or not sender or not base_url:
        raise RuntimeError(
            "Password reset email is not configured: RESEND_API_KEY, "
            "MAIL_FROM and APP_BASE_URL are required."
        )

    reset_url = f"{base_url}/reset-password?token={quote(token, safe='')}"
    subject = "Reset your Nafiz Ahmed password"
    text = (
        "We received a request to reset your password.\n\n"
        f"Reset your password: {reset_url}\n\n"
        "This link expires in 30 minutes and can be used only once. "
        "If you did not request this, you can safely ignore this email.\n"
    )

    payload = json.dumps({
        "from": sender,
        "to": [recipient],
        "subject": subject,
        "text": text,
    }).encode("utf-8")

    request = Request(
        "https://api.resend.com/emails",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "nafiz-ahmed12s-password-reset/1.0",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=20) as response:
            response_body = response.read().decode("utf-8")
            if response.status < 200 or response.status >= 300:
                raise RuntimeError(
                    f"Resend returned HTTP {response.status}: {response_body[:500]}"
                )
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Resend returned HTTP {exc.code}: {body[:500]}"
        ) from exc
    except URLError as exc:
        raise RuntimeError(f"Could not reach Resend API: {exc.reason}") from exc
