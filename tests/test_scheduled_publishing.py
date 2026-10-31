from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, text

from blog_routes import publish_due_articles


def test_publish_due_articles_publishes_only_due_drafts_and_is_idempotent():
    engine = create_engine("sqlite:///:memory:")
    now = datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc)
    with engine.begin() as connection:
        connection.execute(text("""CREATE TABLE blog_articles (
            id INTEGER PRIMARY KEY, status TEXT NOT NULL, scheduled_at DATETIME,
            published_at DATETIME, updated_at DATETIME
        )"""))
        connection.execute(text("""INSERT INTO blog_articles
            (id,status,scheduled_at) VALUES
            (1,'draft',:due),(2,'draft',:future),(3,'published',:past)"""), {
                "due": now - timedelta(minutes=1),
                "future": now + timedelta(minutes=1),
                "past": now - timedelta(days=1),
            })
    from sqlalchemy.orm import Session
    with Session(engine) as db:
        assert publish_due_articles(db, now) == 1
        row = db.execute(text("SELECT status,published_at,scheduled_at FROM blog_articles WHERE id=1")).one()
        assert row.status == "published"
        assert row.published_at is not None
        assert row.scheduled_at is None
        assert publish_due_articles(db, now) == 0
        assert db.execute(text("SELECT status FROM blog_articles WHERE id=2")).scalar_one() == "draft"
