import logging

from flask import jsonify, request


def register_error_handlers(app):
    """Register production-safe error handlers without changing normal routes."""
    app.logger.setLevel(logging.INFO)

    @app.errorhandler(400)
    def handle_bad_request(error):
        app.logger.warning(
            "Bad request: path=%s method=%s remote=%s error=%s",
            request.path,
            request.method,
            request.remote_addr,
            error,
        )
        return _response("bad_request", "Bad request."), 400

    @app.errorhandler(403)
    def handle_forbidden(error):
        app.logger.warning(
            "Forbidden request: path=%s method=%s remote=%s error=%s",
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
            "Request too large: path=%s method=%s remote=%s",
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
            "Unhandled application error: path=%s method=%s remote=%s",
            request.path,
            request.method,
            request.remote_addr,
        )
        return _response("internal_error", "An internal server error occurred."), 500


def _response(code, message):
    """Return JSON for API-style requests and plain text otherwise."""
    if request.path.startswith("/health/") or request.path == "/health" or request.accept_mimetypes.best == "application/json":
        return jsonify({"error": code, "message": message})
    return message
