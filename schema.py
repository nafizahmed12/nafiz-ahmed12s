from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash

from database import SessionLocal
from models import User, Website


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


def authenticate_user(username, password):
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == username.strip()))
        if user and check_password_hash(user.password_hash, password):
            return user
        return None


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


def get_website_by_slug(slug):
    with SessionLocal() as db:
        return db.scalar(select(Website).where(Website.slug == slug.lower()))
