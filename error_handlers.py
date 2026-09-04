import json
import logging
import time
import uuid

from flask import g, jsonify, request, url_for


def register_error_handlers(app):
    """Register production-safe error handlers, request tracing, timing and SEO metadata."""
    app.logger.setLevel(logging.INFO)

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
        """Add accurate search/social metadata and ecommerce structured data to the homepage."""
        if request.path == "/" and response.mimetype == "text/html":
            try:
                html = response.get_data(as_text=True)
                canonical_url = url_for("home", _external=True).rstrip("/")
                old_title = "<title>Nafiz Ecommerce — Shop Phones, Electronics & More</title>"
                new_title = "<title>Nafiz Ecommerce — Phones, Electronics & More in Bangladesh</title>"
                if old_title in html:
                    html = html.replace(old_title, new_title, 1)
                seo_tags = f'''\n<meta name="description" content="Shop phones, laptops, electronics, accessories and more online in Bangladesh with Nafiz Ecommerce.">\n<meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1">\n<link rel="canonical" href="{canonical_url}/">\n<meta property="og:type" content="website">\n<meta property="og:title" content="Nafiz Ecommerce — Phones, Electronics & More in Bangladesh">\n<meta property="og:description" content="Shop phones, laptops, electronics, accessories and more online in Bangladesh with Nafiz Ecommerce.">\n<meta property="og:url" content="{canonical_url}/">\n<meta property="og:site_name" content="Nafiz Ecommerce">\n<meta name="twitter:card" content="summary">\n<meta name="twitter:title" content="Nafiz Ecommerce — Phones, Electronics & More in Bangladesh">\n<meta name="twitter:description" content="Shop phones, laptops, electronics, accessories and more online in Bangladesh with Nafiz Ecommerce.">\n'''
                structured_data = [
                    {
                        "@context": "https://schema.org",
                        "@type": "WebSite",
                        "name": "Nafiz Ecommerce",
                        "url": f"{canonical_url}/",
                        "potentialAction": {
                            "@type": "SearchAction",
                            "target": f"{canonical_url}/shop?q={{search_term_string}}",
                            "query-input": "required name=search_term_string",
                        },
                    },
                    {
                        "@context": "https://schema.org",
                        "@type": "Organization",
                        "name": "Nafiz Ecommerce",
                        "url": f"{canonical_url}/",
                    },
                ]
                # Replace the old personal-profile SEO block if it exists; otherwise add the ecommerce block.
                old_seo_start = '<link rel="canonical" href="'
                if old_seo_start in html and 'Nafiz Ahmed — Python Developer' in html:
                    head_end = html.find("</head>")
                    head_start = html.rfind("<head", 0, head_end)
                    if head_start >= 0:
                        head = html[head_start:head_end]
                        marker = '<link rel="canonical" href="'
                        block_start = head.find(marker)
                        if block_start >= 0:
                            block_end = head.find("</script>", block_start)
                            if block_end >= 0:
                                block_end += len("</script>")
                                html = html[:head_start] + head[:block_start] + seo_tags + "<script type=\"application/ld+json\">" + json.dumps(structured_data, ensure_ascii=False) + "</script>" + head[block_end:] + html[head_end:]
                elif 'name="description"' not in html:
                    html = html.replace("</head>", seo_tags + "<script type=\"application/ld+json\">" + json.dumps(structured_data, ensure_ascii=False) + "</script>\n</head>", 1)
                response.set_data(html)
            except Exception:
                app.logger.exception("Homepage SEO metadata injection failed")
        return response

    @app.after_request
    def add_product_page_seo(response):
        """Normalize product canonicals and add breadcrumb structured data without changing product data."""
        if request.path.startswith("/phone-detail/") and response.status_code == 200 and response.mimetype == "text/html":
            try:
                html = response.get_data(as_text=True)
                canonical_url = request.base_url
                html = html.replace(
                    '<link rel="canonical" href="{{ request.url }}">',
                    f'<link rel="canonical" href="{canonical_url}">',
                    1,
                )

                # Prevent duplicate query-string URLs from becoming separate indexable product URLs.
                robots_tag = '<meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1">'
                if 'name="robots"' not in html:
                    html = html.replace("</head>", robots_tag + "\n</head>", 1)

                # Add descriptive alt text to the primary product image if the template does not provide one.
                if '<div class="main-image-container">' in html:
                    marker = '<div class="main-image-container">'
                    image_start = html.find("<img", html.find(marker))
                    image_end = html.find(">", image_start)
                    if image_start >= 0 and image_end >= 0:
                        image_tag = html[image_start:image_end + 1]
                        if " alt=" not in image_tag:
                            title_marker = '<h1 class="product-title">'
                            title_start = html.find(title_marker)
                            title_end = html.find("</h1>", title_start)
                            product_name = html[title_start + len(title_marker):title_end].strip() if title_start >= 0 and title_end >= 0 else "Product"
                            image_tag_with_alt = image_tag[:-1] + f' alt="{product_name} - Nafiz Store">'
                            html = html[:image_start] + image_tag_with_alt + html[image_end + 1:]

                breadcrumb = {
                    "@context": "https://schema.org",
                    "@type": "BreadcrumbList",
                    "itemListElement": [
                        {"@type": "ListItem", "position": 1, "name": "Home", "item": url_for("home", _external=True)},
                        {"@type": "ListItem", "position": 2, "name": "Smartphones", "item": url_for("shop", _external=True)},
                    ],
                }
                html = html.replace(
                    "</head>",
                    '<script type="application/ld+json">' + json.dumps(breadcrumb, ensure_ascii=False) + '</script>\n</head>',
                    1,
                )
                response.set_data(html)
            except Exception:
                app.logger.exception("Product page SEO optimization failed")
        return response

    @app.after_request
    def attach_shop_design(response):
        """Load the marketplace-style product card enhancement on the shop page."""
        if request.path == "/shop" and response.status_code == 200 and "text/html" in response.content_type:
            body = response.get_data(as_text=True)
            marker = '<script src="/static/shop-enhance.js" defer></script>'
            if marker not in body and "</body>" in body:
                response.set_data(body.replace("</body>", marker + "</body>", 1))
        return response

    @app.after_request
    def finalize_security_headers(response):
        """Apply the strictest CSP compatible with the current application."""
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
        app.logger.info("not_found request_id=%s method=%s path=%s remote=%s", getattr(g, "request_id", "-"), request.method, request.path, request.remote_addr)
        return _response("not_found", "The requested resource was not found."), 404

    @app.errorhandler(413)
    def handle_request_too_large(error):
        app.logger.warning("request_too_large request_id=%s path=%s method=%s remote=%s", getattr(g, "request_id", "-"), request.path, request.method, request.remote_addr)
        return _response("request_too_large", "Request is too large."), 413

    @app.errorhandler(429)
    def handle_rate_limited(error):
        app.logger.warning("rate_limited request_id=%s path=%s method=%s remote=%s", getattr(g, "request_id", "-"), request.path, request.method, request.remote_addr)
        return _response("rate_limited", "Too many requests. Please try again later."), 429

    @app.errorhandler(500)
    def handle_internal_error(error):
        app.logger.exception("internal_error request_id=%s path=%s method=%s remote=%s", getattr(g, "request_id", "-"), request.path, request.method, request.remote_addr)
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
