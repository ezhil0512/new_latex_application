"""Unit tests for the Flask presentation layer and routes."""

from uuid import uuid4
from new_latex_app.presentation.flask_app import create_app


def test_flask_app_home_json() -> None:
    """Home page should return JSON metadata when requested by default or JSON clients."""
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        res = client.get("/")
        assert res.status_code == 200
        assert res.is_json
        data = res.get_json()
        assert data["service"] == "Image-to-LaTeX Generator"
        assert "endpoints" in data


def test_flask_app_home_html() -> None:
    """Home page should render the index.html template when text/html is requested explicitly."""
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        res = client.get("/", headers={"Accept": "text/html"})
        assert res.status_code == 200
        assert not res.is_json
        html = res.get_data(as_text=True)
        assert "<!DOCTYPE html>" in html
        assert "Offline Image &amp; PDF to LaTeX" in html


def test_flask_app_home_html_browser() -> None:
    """Home page should render the index.html template when standard browser Accept headers are sent."""
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        browser_accept = "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
        res = client.get("/", headers={"Accept": browser_accept})
        assert res.status_code == 200
        assert not res.is_json
        html = res.get_data(as_text=True)
        assert "<!DOCTYPE html>" in html
        assert "Offline Image &amp; PDF to LaTeX" in html


def test_flask_app_home_json_any() -> None:
    """Home page should return JSON metadata when Accept header is */* (like curl)."""
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        res = client.get("/", headers={"Accept": "*/*"})
        assert res.status_code == 200
        assert res.is_json
        data = res.get_json()
        assert data["service"] == "Image-to-LaTeX Generator"


def test_flask_app_preview_asset_validation() -> None:
    """Asset endpoint should validate UUID format and handle missing files gracefully."""
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        # Invalid UUID format
        res = client.get("/preview/invalid-uuid/assets/diagram_1.png")
        assert res.status_code == 400
        assert res.get_json()["error"] == "Invalid session ID format"

        # Correct UUID format, but session not found
        random_session = str(uuid4())
        res = client.get(f"/preview/{random_session}/assets/diagram_1.png")
        assert res.status_code == 404
        assert res.get_json()["error"] == "Export package not found"


def test_flask_app_preview_asset_traversal_prevention() -> None:
    """Asset endpoint should prevent path traversal attacks."""
    app = create_app()
    app.config["TESTING"] = True
    random_session = str(uuid4())
    
    with app.test_client() as client:
        # Prevent traversal in the asset filename parameter using directory dots
        res_dots = client.get(f"/preview/{random_session}/assets/../../secret.txt")
        assert res_dots.status_code in (400, 404)

        # Prevent traversal containing separator slashes
        res_slash = client.get(f"/preview/{random_session}/assets/subfolder/diagram_1.png")
        assert res_slash.status_code in (400, 404)
        
        # Prevent traversal containing backslashes
        res_backslash = client.get(f"/preview/{random_session}/assets/subfolder\\diagram_1.png")
        assert res_backslash.status_code in (400, 404)


def test_flask_app_download_endpoint() -> None:
    """Download endpoint should validate UUID format and handle non-existent sessions gracefully."""
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        # Invalid UUID format
        res = client.get("/download/invalid-uuid")
        assert res.status_code == 400
        assert res.get_json()["error"] == "Invalid session ID format"

        # Correct UUID format, but session not found
        random_session = str(uuid4())
        res = client.get(f"/download/{random_session}")
        assert res.status_code == 404
        assert res.get_json()["error"] == "Export package not found"

