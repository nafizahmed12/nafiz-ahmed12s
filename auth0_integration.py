import os
import re
import secrets

from dotenv import load_dotenv
from flask import session
from werkzeug.security import generate_password_hash

from database import SessionLocal
from models import User

load_dotenv()


class FlaskSessionStore:
    """Small async store backed by Flask's signed session cookie."""

    async def get(self, key, options=None):
        return session.get(key)

    async def set(self, key, value, options=None):
        session[key] = value

    async def delete(self, key, options=None):
        session.pop(key, None)

    async def delete_by_logout_token(self, claims, options=None):
        return None


def auth0_is_configured():
    return all(
        os.getenv(name, "").strip()
        for name in (
            "AUTH0_DOMAIN",
            "AUTH0_CLIENT_ID",
            "AUTH0_CLIENT_SECRET",
            "AUTH0_SECRET",
            "AUTH0_REDIRECT_URI",
        )
    )


def get_auth0_client():
    if not auth0_is_configured():
        return None

    from auth0_server_python.auth_server.server_client import ServerClient

    store = FlaskSessionStore()
    return ServerClient(
        domain=os.environ["AUTH0_DOMAIN"].strip(),
        client_id=os.environ["AUTH0_CLIENT_ID"].strip(),
        client_secret=os.environ["AUTH0_CLIENT_SECRET"].strip(),
        secret=os.environ["AUTH0_SECRET"].strip(),
        redirect_uri=os.environ["AUTH0_REDIRECT_URI"].strip(),
        state_store=store,
        transaction_store=store,
        authorization_params={
            "scope": "openid profile email",
        },
    )


def _username_base(profile):
    raw = profile.get("nickname") or profile.get("name") or profile.get("email", "").split("@")[0]
    value = re.sub(r"[^a-zA-Z0-9_-]+", "-", str(raw)).strip("-_").lower()
    return (value or "auth0-user")[:60]


def get_or_create_local_user(profile):
    email = str(profile.get("email") or "").strip().lower()
    if not email:
        raise ValueError("Auth0 did not provide an email address.")
    if profile.get("email_verified") is not True:
        raise ValueError("Please verify your email address in Auth0 before signing in.")

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email).first()
        if user is not None:
            return user.id, user.username

        base = _username_base(profile)
        username = base
        counter = 1
        while db.query(User).filter(User.username == username).first() is not None:
            suffix = f"-{counter}"
            username = f"{base[:80-len(suffix)]}{suffix}"
            counter += 1

        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(secrets.token_urlsafe(32)),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user.id, user.username
