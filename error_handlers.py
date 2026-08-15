import json
import logging
import uuid

from flask import g, jsonify, request, url_for

from admin_security import register_admin_session_guard


def register_error_handlers(app):
    """Register production-safe error handlers and homepage SEO metadata."""
    app.logger.setLevel(logging.INFO)
    register_admin_session_guard(app)

    @app.before_request
    def assign_request_id():
        """Give every request a short correlation ID for production debugging."""
        incoming = request.headers.get("X-Request-ID", "").strip()
        g.request_id = incoming[:80] if incoming else uuid.uuid4().hex

    @app.after_request
    def add_request_id(response):
        """Expose the request correlation ID without trusting it as application data."""
        response.headers["X-Request-ID"] = getattr(g, "request_id", "")
        return response

    @app.after_request
    def add_homepage_seo(response):
        """Add canonical/social metadata to the public homepage without changing its UI."""
        if request.path == "/" and response.mimetype == "text/html":
            try:
                html = response.get_data(as_text=True)
                if "rel=\"canonical\"" not in html and "property=\"og:title\"" not in html:
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

    @app.errorhandler(400)
    def handle_bad_request(error):
        app.logger.warning(
            "Bad request: request_id=%s path=%s method=%s remote=%s error=%s",
            getattr(g, "request_id", "-"),
            request.path,
            request.method,
            request.remote_addr,
            error,
        )
        return _response("bad_request", "Bad request."), 400

    @app.errorhandler(403)
    def handle_forbidden(error):
        app.logger.warning(
            "Forbidden request: request_id=%s path=%s method=%s remote=%s error=%s",
            getattr(g, "request_id", "-"),
            request.path,
            request.method,
            request.remote_addr,
            error,
        )
        return _response("forbidden", "Access denied."), 403

    @app.errorhandler(404)
    def handle_not_found(error):
        return _response("not_found", "The requested resource was not found."), 404

    @app.errorhandler(413)
    def handle_request_too_large(error):
        app.logger.warning(
            "Request too large: request_id=%s path=%s method=%s remote=%s",
            getattr(g, "request_id", "-"),
            request.path,
            request.method,
            request.remote_addr,
        )
        return _response("request_too_large", "Request is too large."), 413

    @app.errorhandler(429)
    def handle_rate_limited(error):
        return _response("rate_limited", "Too many requests. Please try again later."), 429

    @app.errorhandler(500)
    def handle_internal_error(error):
        app.logger.exception(
            "Unhandled application error: request_id=%s path=%s method=%s remote=%s",
            getattr(g, "request_id", "-"),
            request.path,
            request.method,
            request.remote_addr,
        )
        return _response("internal_error", "An internal server error occurred."), 500


def _response(code, message):
    """Return JSON for API-style requests and plain text otherwise."""
    if request.path.startswith("/health/") or request.path == "/health" or request.accept_mimetypes.best == "application/json":
        payload = {"error": code, "message": message}
        if getattr(g, "request_id", None):
            payload["request_id"] = g.request_id
        return jsonify(payload)
    return message
