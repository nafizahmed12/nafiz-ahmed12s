# Nafiz Ahmed — Commerce Platform

A Flask + PostgreSQL commerce platform with authentication, admin/seller workflows, orders, payments, digital products, affiliate functionality, security controls, Alembic migrations, and automated tests.

## Stack

- Python / Flask
- SQLAlchemy + PostgreSQL
- Alembic migrations
- Gunicorn
- pytest
- GitHub Actions

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export SECRET_KEY='change-me'
export DATABASE_URL='postgresql://user:password@localhost:5432/nafiz'
export ADMIN_USERNAME='admin'
export ADMIN_PASSWORD='change-me'
export ADMIN_EMAIL='you@example.com'

alembic upgrade head
python app.py
```

## Production checklist

1. Set a strong random `SECRET_KEY`.
2. Use PostgreSQL; do not rely on SQLite for production commerce data.
3. Run `alembic upgrade head` during deployment.
4. Configure payment credentials and `PAYMENT_WEBHOOK_SECRET` only through the hosting provider's secret/environment settings.
5. Set `APP_BASE_URL` to the real HTTPS domain.
6. Configure email delivery for password resets and order notifications.
7. Keep payment callbacks server-validated and signed.
8. Run the test suite before every deployment.

## Monetization path

The application is designed to support several revenue channels:

- Digital products: sell downloadable files, templates, code, guides, and other digital goods.
- Services: offer Python, Flask, automation, and website-development services.
- Marketplace/commerce: onboard sellers and earn commissions on completed orders.
- Affiliate marketing: publish products with tracked affiliate links and earn commissions.
- Advertising: add AdSense only after building useful public content and consistent traffic.

### Recommended launch order

**1. Services + digital products → 2. Marketplace commissions → 3. Affiliate content → 4. Advertising.**

Do not treat AdSense as the primary revenue source at launch; it normally requires meaningful traffic to become useful.

## Testing

```bash
pytest -q
```

The CI workflow also validates Python compilation, application import, health endpoints, PostgreSQL migrations, and regression tests.

## Security

The project includes password hashing, session controls, CSRF protection, rate limiting, security headers, signed payment webhooks, and password-reset token hashing. Review production environment variables and payment configuration before accepting real customer payments.
