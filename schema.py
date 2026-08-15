from datetime import datetime, timedelta, timezone

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


def allow_registration(ip_address, limit=10, window_seconds=3600):
    key = (ip_address or "unknown").strip()[:255] or "unknown"
    return _allow_rate_limited_request(
        "registration_rate_limits", key, limit, window_seconds
    )


def allow_login(ip_address, identifier, limit=10, window_seconds=900):
    ip_key = (ip_address or "unknown").strip()[:200] or "unknown"
    identity_key = (identifier or "unknown").strip().lower()[:255] or "unknown"
    key = f"{ip_key}:{identity_key}"
    return _allow_rate_limited_request(
        "login_rate_limits", key, limit, window_seconds
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
        website = Website(
            owner_id=owner_id,
            name=name.strip(),
            slug=slug.strip().lower(),
            title=title,
            content=content,
        )
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
        return list(
            db.scalars(
                select(Website)
                .where(Website.owner_id == owner_id)
                .order_by(Website.id.desc())
            )
        )


def delete_website(owner_id, website_id):
    with SessionLocal() as db:
        website = db.scalar(
            select(Website).where(
                Website.id == website_id,
                Website.owner_id == owner_id,
            )
        )
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
    page = max(1, int(page))
    per_page = max(1, min(int(per_page), 100))
    offset = (page - 1) * per_page
    with SessionLocal() as db:
        messages = list(
            db.scalars(
                select(Message)
                .order_by(Message.id.desc())
                .offset(offset)
                .limit(per_page)
            )
        )
        total = db.scalar(select(func.count()).select_from(Message)) or 0
        return messages, total


def get_subscribers(page=1, per_page=50):
    """Return newsletter subscribers with pagination for the admin dashboard."""
    page = max(1, int(page))
    per_page = max(1, min(int(per_page), 100))
    offset = (page - 1) * per_page
    with SessionLocal() as db:
        subscribers = list(
            db.scalars(
                select(Subscriber)
                .order_by(Subscriber.id.desc())
                .offset(offset)
                .limit(per_page)
            )
        )
        total = db.scalar(select(func.count()).select_from(Subscriber)) or 0
        return subscribers, total
