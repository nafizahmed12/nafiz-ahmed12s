import os
import smtplib
from email.message import EmailMessage
from urllib.parse import quote


def send_password_reset_email(recipient, token):
    host = os.getenv("SMTP_HOST", "").strip()
    username = os.getenv("SMTP_USERNAME", "").strip()
    password = os.getenv("SMTP_PASSWORD", "")
    sender = os.getenv("MAIL_FROM", username).strip()
    port = int(os.getenv("SMTP_PORT", "587"))
    base_url = os.getenv("APP_BASE_URL", "").strip().rstrip("/")
    if not host or not sender or not base_url:
        raise RuntimeError("Password reset email is not configured.")

    reset_url = f"{base_url}/reset-password?token={quote(token, safe='')}"
    message = EmailMessage()
    message["Subject"] = "Reset your Nafiz Ahmed password"
    message["From"] = sender
    message["To"] = recipient
    message.set_content(
        "We received a request to reset your password.\n\n"
        f"Reset your password: {reset_url}\n\n"
        "This link expires in 30 minutes and can be used only once. "
        "If you did not request this, you can safely ignore this email.\n"
    )

    with smtplib.SMTP(host, port, timeout=15) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        if username:
            smtp.login(username, password)
        smtp.send_message(message)
