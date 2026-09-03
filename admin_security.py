    @app.before_request
    def guard_admin_session():
        if not session.get("admin_logged_in"):
            return None
        def reject_admin_session():
            _clear_admin_session()
            if request.path.startswith("/api/"):
                return jsonify({"error": "Admin authentication required."}), 401
            return redirect(url_for("login"))
        if session.get("admin_role") != ADMIN_ROLE:
            return reject_admin_session()
        configured_username = os.getenv("ADMIN_USERNAME", "").strip()
        session_username = str(session.get("admin_username", "")).strip()
        if not configured_username or not session_username or not hmac.compare_digest(session_username, configured_username):
            return reject_admin_session()
        now = datetime.now(timezone.utc).timestamp()
        try:
            authenticated_at = float(session.get("admin_authenticated_at")); last_activity = float(session.get("admin_last_activity"))
        except (TypeError, ValueError):
            return reject_admin_session()
        if now - authenticated_at > ADMIN_ABSOLUTE_TIMEOUT_SECONDS or now - last_activity > ADMIN_IDLE_TIMEOUT_SECONDS:
            return reject_admin_session()
        session["admin_last_activity"] = now

    @app.before_request
    def guard_user_session():
        user_id = session.get("user_id")
        if not user_id or session.get("admin_logged_in"):
            return None
        protected_prefixes = (
            "/dashboard", "/account", "/orders", "/api/cart", "/api/checkout",
            "/api/orders", "/api/payments", "/seller", "/supplier",
        )
        if not any(request.path == prefix or request.path.startswith(prefix + "/") for prefix in protected_prefixes):
            return None
        try:
            created_ts = float(session.get(USER_SESSION_CREATED_KEY))
        except (TypeError, ValueError):
            session.clear(); return redirect(url_for("user_login"))
        with SessionLocal() as db:
            changed_at = db.execute(text("SELECT password_changed_at FROM users WHERE id=:uid"), {"uid": user_id}).scalar_one_or_none()
        if changed_at is not None:
            if changed_at.tzinfo is None: changed_at = changed_at.replace(tzinfo=timezone.utc)
            if created_ts < changed_at.timestamp():
                session.clear(); return redirect(url_for("user_login"))

    @app.after_request
    def rewrite_iphone_seo_urls(response):
        if request.path in {"/iphone-18", "/iphone-18-pro", "/iphone-18-pro-max"} and response.status_code == 200 and "text/html" in response.content_type:
            # send_file() responses use direct passthrough mode, so disable it
            # before reading the response body for the SEO link rewrite.
            response.direct_passthrough = False
            body = response.get_data(as_text=True)
            replacements = {
                "/static/iphone-18-pro-max.html": "/iphone-18-pro-max",
                "/static/iphone-18-pro.html": "/iphone-18-pro",
                "/static/iphone-18.html": "/iphone-18",
            }
            for old, new in replacements.items():
                body = body.replace(old, new)
            response.set_data(body)
        return response

    @app.after_request
    def attach_home_javascript(response):
        if request.path == "/" and response.status_code == 200 and "text/html" in response.content_type:
            body = response.get_data(as_text=True)
            marker = '<script src="/static/home.js" defer></script>'
            if marker not in body and "</body>" in body:
                response.set_data(body.replace("</body>", marker + "</body>"))
        return response

    @app.after_request
    def harden_content_security_policy(response):