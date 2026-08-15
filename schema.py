from sqlalchemy import select
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


def get_messages():
    with SessionLocal() as db:
        return list(db.scalars(select(Message).order_by(Message.id.desc())))
