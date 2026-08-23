from datetime import datetime, timedelta, timezone
import hashlib
import secrets

from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash

from database import SessionLocal
from models import User, Website, Message, Subscriber


def create_user(username, email, password):
    with SessionLocal() as db:
        user = User(
            username=username.strip(),
            email=email.strip().lower(),
            password_hash=generate_password_hash(password),
        )
        db.add(user)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            return None
        db.refresh(user)
        return user


def _allow_rate_limited_request(table_name, key, limit, window_seconds):
    """Atomically allow requests using shared PostgreSQL storage."""
    now = datetime.now(timezone.utc)
    window = timedelta(seconds=window_seconds)

    with SessionLocal() as db:
        if db.bind.dialect.name == "postgresql":
            result = db.execute(
                text(f"""
                    INSERT INTO {table_name}
                        (rate_key, window_started_at, request_count)
                    VALUES (:key, :now, 1)
                    ON CONFLICT (rate_key) DO UPDATE SET
                        request_count = CASE
                            WHEN {table_name}.window_started_at <= :cutoff
                                THEN 1
                            ELSE {table_name}.request_count + 1
                        END,
                        window_started_at = CASE
                            WHEN {table_name}.window_started_at <= :cutoff
                                THEN :now
                            ELSE {table_name}.window_started_at
                        END
                    RETURNING request_count
                """),
                {"key": key, "now": now, "cutoff": now - window},
            ).scalar_one()
            db.commit()
            return result <= limit

        row = db.execute(
            text(f"SELECT window_started_at, request_count FROM {table_name} WHERE rate_key = :key"),
            {"key": key},
        ).first()
        if row is None:
            db.execute(
                text(f"INSERT INTO {table_name} (rate_key, window_started_at, request_count) VALUES (:key, :now, 1)"),
                {"key": key, "now": now},
            )
            db.commit()
            return True

        started_at = row.window_started_at
        if isinstance(started_at, str):
            started_at = datetime.fromisoformat(started_at)
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)

        if now - started_at >= window:
            db.execute(
                text(f"UPDATE {table_name} SET window_started_at = :now, request_count = 1 WHERE rate_key = :key"),
                {"key": key, "now": now},
            )
            db.commit()
            return True

        if row.request_count >= limit:
            db.rollback()
            return False

        db.execute(
            text(f"UPDATE {table_name} SET request_count = request_count + 1 WHERE rate_key = :key"),
            {"key": key},
        )
        db.commit()
        return True


def _safe_rate_key(value, max_length=255):
    return (value or "unknown").strip()[:max_length] or "unknown"


def allow_registration(ip_address, limit=10, window_seconds=3600):
    key = _safe_rate_key(ip_address)
    return _allow_rate_limited_request("registration_rate_limits", key, limit, window_seconds)


def allow_login(ip_address, identifier, limit=10, window_seconds=900):
    ip_key = _safe_rate_key(ip_address, 200)
    identity_key = _safe_rate_key(identifier, 255).lower()
    key = f"{ip_key}:{identity_key}"
    return _allow_rate_limited_request("login_rate_limits", key, limit, window_seconds)


def allow_contact(ip_address, limit=5, window_seconds=900):
    key = _safe_rate_key(ip_address)
    return _allow_rate_limited_request("contact_rate_limits", key, limit, window_seconds)


def allow_subscription(ip_address, limit=10, window_seconds=3600):
    key = _safe_rate_key(ip_address)
    return _allow_rate_limited_request("subscribe_rate_limits", key, limit, window_seconds)


def allow_cart_action(ip_address, user_id, limit=60, window_seconds=60):
    ip_key = _safe_rate_key(ip_address, 200)
    user_key = _safe_rate_key(str(user_id) if user_id else None, 50)
    key = f"{ip_key}:{user_key}"
    return _allow_rate_limited_request("cart_rate_limits", key, limit, window_seconds)


def allow_checkout(ip_address, user_id, limit=10, window_seconds=300):
    ip_key = _safe_rate_key(ip_address, 200)
    user_key = _safe_rate_key(str(user_id) if user_id else None, 50)
    key = f"{ip_key}:{user_key}"
    return _allow_rate_limited_request("checkout_rate_limits", key, limit, window_seconds)


def allow_payment_attempt(ip_address, user_id, limit=10, window_seconds=600):
    ip_key = _safe_rate_key(ip_address, 200)
    user_key = _safe_rate_key(str(user_id) if user_id else None, 50)
    key = f"{ip_key}:{user_key}"
    return _allow_rate_limited_request("payment_rate_limits", key, limit, window_seconds)


def allow_password_reset(ip_address, identifier, limit=5, window_seconds=900):
    ip_key = _safe_rate_key(ip_address, 200)
    identity_key = _safe_rate_key(identifier, 255).lower()
    return _allow_rate_limited_request(
        "login_rate_limits", f"password-reset:{ip_key}:{identity_key}", limit, window_seconds
    )


def authenticate_user(identifier, password):
    identifier = identifier.strip()
    with SessionLocal() as db:
        user = db.scalar(
            select(User).where(
                (User.username == identifier) | (User.email == identifier.lower())
            )
        )
        if user and check_password_hash(user.password_hash, password):
            return user
        return None


def get_user(user_id):
    with SessionLocal() as db:
        return db.get(User, user_id)


def create_password_reset_token(identifier, expires_minutes=30):
    """Return (token, email) for a valid user, otherwise (None, None)."""
    identifier = (identifier or "").strip()
    if not identifier:
        return None, None
    with SessionLocal() as db:
        user = db.scalar(
            select(User).where(
                (User.username == identifier) | (User.email == identifier.lower())
            )
        )
        if user is None:
            return None, None
        now = datetime.now(timezone.utc)
        db.execute(
            text("DELETE FROM password_reset_tokens WHERE user_id=:uid OR expires_at <= :now"),
            {"uid": user.id, "now": now},
        )
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        db.execute(
            text("""INSERT INTO password_reset_tokens
                (user_id, token_hash, expires_at, created_at)
                VALUES (:uid, :hash, :expires, :created)"""),
            {
                "uid": user.id,
                "hash": token_hash,
                "expires": now + timedelta(minutes=expires_minutes),
                "created": now,
            },
        )
        db.commit()
        return token, user.email


def reset_password_with_token(token, new_password):
    if not token or len(new_password or "") < 8:
        return False
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        row = db.execute(
            text("""SELECT id, user_id FROM password_reset_tokens
                   WHERE token_hash=:hash AND used_at IS NULL AND expires_at > :now
                   LIMIT 1"""),
            {"hash": token_hash, "now": now},
        ).mappings().first()
        if row is None:
            return False
        user = db.get(User, row["user_id"])
        if user is None:
            return False
        user.password_hash = generate_password_hash(new_password)
        db.execute(
            text("UPDATE password_reset_tokens SET used_at=:now WHERE id=:id"),
            {"now": now, "id": row["id"]},
        )
        db.commit()
        return True


def update_user_profile(user_id, username, email):
    with SessionLocal() as db:
        user = db.get(User, user_id)
        if user is None:
            return False, "User not found."
        user.username = username.strip()
        user.email = email.strip().lower()
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            return False, "Username or email is already in use."
        return True, "Profile updated successfully."


def change_password(user_id, current_password, new_password):
    with SessionLocal() as db:
        user = db.get(User, user_id)
        if user is None or not check_password_hash(user.password_hash, current_password):
            return False, "Current password is incorrect."
        if len(new_password) < 8:
            return False, "New password must be at least 8 characters."
        if current_password == new_password:
            return False, "New password must be different from the current password."
        user.password_hash = generate_password_hash(new_password)
        db.commit()
        return True, "Password changed successfully."


def create_website(owner_id, name, slug, title="My Website", content=""):
    with SessionLocal() as db:
        website = Website(owner_id=owner_id, name=name.strip(), slug=slug.strip().lower(), title=title, content=content)
        db.add(website)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            return None
        db.refresh(website)
        return website


def get_user_websites(owner_id):
    with SessionLocal() as db:
        return list(db.scalars(select(Website).where(Website.owner_id == owner_id).order_by(Website.id.desc())))


def delete_website(owner_id, website_id):
    with SessionLocal() as db:
        website = db.scalar(select(Website).where(Website.id == website_id, Website.owner_id == owner_id))
        if website is None:
            return False
        db.delete(website)
        db.commit()
        return True


def get_website_by_slug(slug):
    with SessionLocal() as db:
        return db.scalar(select(Website).where(Website.slug == slug.lower()))


def create_message(name, email, message):
    with SessionLocal() as db:
        db.add(Message(name=name.strip(), email=email.strip().lower(), message=message.strip()))
        db.commit()
        return True


def create_subscriber(email):
    with SessionLocal() as db:
        subscriber = Subscriber(email=email.strip().lower())
        db.add(subscriber)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            return False
        return True


def get_messages(page=1, per_page=50):
    page = max(1, int(page)); per_page = max(1, min(int(per_page), 100)); offset = (page - 1) * per_page
    with SessionLocal() as db:
        messages = list(db.scalars(select(Message).order_by(Message.id.desc()).offset(offset).limit(per_page)))
        total = db.scalar(select(func.count()).select_from(Message)) or 0
        return messages, total


def get_subscribers(page=1, per_page=50):
    page = max(1, int(page)); per_page = max(1, min(int(per_page), 100)); offset = (page - 1) * per_page
    with SessionLocal() as db:
        subscribers = list(db.scalars(select(Subscriber).order_by(Subscriber.id.desc()).offset(offset).limit(per_page)))
        total = db.scalar(select(func.count()).select_from(Subscriber)) or 0
        return subscribers, total


def get_admin_stats():
    with SessionLocal() as db:
        return {
            "users": db.scalar(select(func.count()).select_from(User)) or 0,
            "websites": db.scalar(select(func.count()).select_from(Website)) or 0,
            "messages": db.scalar(select(func.count()).select_from(Message)) or 0,
            "subscribers": db.scalar(select(func.count()).select_from(Subscriber)) or 0,
        }
