import json
import logging
import time
import uuid

from flask import g, jsonify, request, url_for

from admin_security import register_admin_session_guard


def register_error_handlers(app):
    """Register production-safe error handlers, request tracing, timing and SEO metadata."""
    app.logger.setLevel(logging.INFO)
    register_admin_session_guard(app)

    @app.before_request
    def assign_request_context():
        """Give every request a correlation ID and start a monotonic timer."""
        incoming = request.headers.get("X-Request-ID", "").strip()
        g.request_id = incoming[:80] if incoming else uuid.uuid4().hex
        g.request_started_at = time.monotonic()

    @app.after_request
    def add_request_metadata(response):
        """Expose safe request metadata for debugging and monitoring."""
        response.headers["X-Request-ID"] = getattr(g, "request_id", "")
        started = getattr(g, "request_started_at", None)
        if started is not None:
            duration_ms = (time.monotonic() - started) * 1000
            response.headers["Server-Timing"] = f"app;dur={duration_ms:.1f}"
            app.logger.info(
                "request_complete request_id=%s method=%s path=%s status=%s duration_ms=%.1f remote=%s",
                getattr(g, "request_id", "-"), request.method, request.path,
                response.status_code, duration_ms, request.remote_addr,
            )
        return response

    @app.after_request
    def add_homepage_seo(response):
        """Add canonical/social metadata to the public homepage without changing its UI."""
        if request.path == "/" and response.mimetype == "text/html":
            try:
                html = response.get_data(as_text=True)
                if 'rel="canonical"' not in html and 'property="og:title"' not in html:
                    canonical_url = url_for("home", _external=True)
                    structured_data = {
                        "@context": "https://schema.org",
                        "@type": "Person",
                        "name": "Nafiz Ahmed",
                        "url": canonical_url,
                        "jobTitle": "Python Developer",
                        "description": "Nafiz Ahmed — Python developer focused on web development, APIs and digital solutions.",
                    }
                    seo_tags = f'''\n    <link rel="canonical" href="{canonical_url}">\n    <meta property="og:type" content="website">\n    <meta property="og:title" content="Nafiz Ahmed — Python Developer">\n    <meta property="og:description" content="Python developer focused on web development, APIs and digital solutions.">\n    <meta property="og:url" content="{canonical_url}">\n    <meta property="og:image" content="{url_for('static', filename='profile.jpg', _external=True)}">\n    <meta name="twitter:card" content="summary">\n    <meta name="twitter:title" content="Nafiz Ahmed — Python Developer">\n    <meta name="twitter:description" content="Python developer focused on web development, APIs and digital solutions.">\n    <meta name="twitter:image" content="{url_for('static', filename='profile.jpg', _external=True)}">\n    <script type="application/ld+json">{json.dumps(structured_data, ensure_ascii=False)}</script>'''
                    html = html.replace("</head>", seo_tags + "\n</head>", 1)
                    response.set_data(html)
            except Exception:
                app.logger.exception("Homepage SEO metadata injection failed")
        return response

    @app.after_request
    def finalize_security_headers(response):
        """Apply the strictest CSP compatible with the current application.

        The application still contains inline handlers/scripts, so removing
        unsafe-inline completely would break existing UI. External JavaScript
        execution is nevertheless blocked; a future frontend refactor can
        remove unsafe-inline and move to nonces/hashes.
        """
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; base-uri 'self'; object-src 'none'; "
            "frame-ancestors 'none'; form-action 'self'; "
            "img-src 'self' data: https:; font-src 'self' data: https:; "
            "style-src 'self' 'unsafe-inline' https:; "
            "script-src 'self' 'unsafe-inline'; connect-src 'self'; "
            "media-src 'self' https:; worker-src 'self'; manifest-src 'self';"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()"
        if request.is_secure:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    @app.errorhandler(400)
    def handle_bad_request(error):
        _log_client_error("bad_request", error)
        return _response("bad_request", "Bad request."), 400

    @app.errorhandler(403)
    def handle_forbidden(error):
        _log_client_error("forbidden", error)
        return _response("forbidden", "Access denied."), 403

    @app.errorhandler(404)
    def handle_not_found(error):
        app.logger.info(
            "not_found request_id=%s method=%s path=%s remote=%s",
            getattr(g, "request_id", "-"), request.method, request.path, request.remote_addr,
        )
        return _response("not_found", "The requested resource was not found."), 404

    @app.errorhandler(413)
    def handle_request_too_large(error):
        app.logger.warning(
            "request_too_large request_id=%s path=%s method=%s remote=%s",
            getattr(g, "request_id", "-"), request.path, request.method, request.remote_addr,
        )
        return _response("request_too_large", "Request is too large."), 413

    @app.errorhandler(429)
    def handle_rate_limited(error):
        app.logger.warning(
            "rate_limited request_id=%s path=%s method=%s remote=%s",
            getattr(g, "request_id", "-"), request.path, request.method, request.remote_addr,
        )
        return _response("rate_limited", "Too many requests. Please try again later."), 429

    @app.errorhandler(500)
    def handle_internal_error(error):
        app.logger.exception(
            "internal_error request_id=%s path=%s method=%s remote=%s",
            getattr(g, "request_id", "-"), request.path, request.method, request.remote_addr,
        )
        return _response("internal_error", "An internal server error occurred."), 500


def _log_client_error(code, error):
    logging.getLogger("app").warning(
        "%s request_id=%s path=%s method=%s remote=%s error=%s",
        code, getattr(g, "request_id", "-"), request.path,
        request.method, request.remote_addr, error,
    )


def _response(code, message):
    """Return JSON for API-style requests and plain text otherwise."""
    wants_json = (
        request.path.startswith("/api/")
        or request.path.startswith("/health/")
        or request.path == "/health"
        or request.accept_mimetypes.best == "application/json"
    )
    if wants_json:
        payload = {"error": code, "message": message}
        if getattr(g, "request_id", None):
            payload["request_id"] = g.request_id
        return jsonify(payload)
    return message
