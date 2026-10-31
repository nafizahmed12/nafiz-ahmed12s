from publisher_admin_routes import normalize_bulk_article_action


def test_bulk_action_accepts_only_supported_actions():
    assert normalize_bulk_article_action("publish") == "publish"
    assert normalize_bulk_article_action("draft") == "draft"
    assert normalize_bulk_article_action("delete") == "delete"
    assert normalize_bulk_article_action("invalid") is None


def test_bulk_article_ids_are_deduplicated_and_bounded():
    from publisher_admin_routes import normalize_bulk_article_ids

    assert normalize_bulk_article_ids(["2", "2", "7"]) == [2, 7]
    assert normalize_bulk_article_ids(["x", "-1", "0"]) == []
    assert normalize_bulk_article_ids([str(i) for i in range(1, 103)]) == []


def test_bulk_editor_route_is_registered_and_admin_only():
    import wsgi

    routes = {rule.rule for rule in wsgi.app.url_map.iter_rules()}
    assert "/admin/bulk" in routes
    response = wsgi.app.test_client().get("/admin/bulk")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")
