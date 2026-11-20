"""The API serves the built dashboard without shadowing API routes."""

from pathlib import Path

from app.web import mount_dashboard
from fastapi import FastAPI
from fastapi.testclient import TestClient


def make_client(tmp_path: Path) -> TestClient:
    tmp_path.mkdir()
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "app-abc.js").write_text("console.log(1)")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "index.html").write_text("<p>docs</p>")
    (tmp_path / "index.html").write_text("<div id=root></div>")
    (tmp_path.parent / "secret.txt").write_text("nope")
    app = FastAPI(docs_url=None, redoc_url=None)

    @app.get("/fairness/report")
    def report() -> dict[str, str]:
        return {"ok": "api"}

    assert mount_dashboard(app, tmp_path)
    return TestClient(app)


def test_spa_routes_and_files(tmp_path: Path) -> None:
    c = make_client(tmp_path / "dist")
    assert c.get("/").text == "<div id=root></div>"
    assert c.get("/applicant/42").text == "<div id=root></div>"
    assert c.get("/docs").text == "<p>docs</p>"
    r = c.get("/assets/app-abc.js")
    assert r.status_code == 200 and "immutable" in r.headers["cache-control"]


def test_api_wins_and_unknown_is_json_404(tmp_path: Path) -> None:
    c = make_client(tmp_path / "dist")
    assert c.get("/fairness/report").json() == {"ok": "api"}
    assert c.get("/nope").status_code == 404
    assert c.get("/../secret.txt").status_code == 404
    assert c.get("/%2e%2e/secret.txt").status_code == 404


def test_not_mounted_without_build(tmp_path: Path) -> None:
    assert not mount_dashboard(FastAPI(), tmp_path)


def test_borrower_web_app_deep_links(tmp_path: Path) -> None:
    from app.web import mount_borrower_app

    web = tmp_path / "web"
    web.mkdir()
    (web / "index.html").write_text("<base href='/app/'>flutter")
    (web / "main.dart.js").write_text("main()")
    app = FastAPI(docs_url=None, redoc_url=None)
    assert mount_borrower_app(app, web)
    c = TestClient(app)
    assert c.get("/app", follow_redirects=False).status_code == 307
    assert "flutter" in c.get("/app/").text
    assert "flutter" in c.get("/app/score").text  # deep link -> index.html
    assert c.get("/app/main.dart.js").text == "main()"
    assert c.get("/app/missing.js").status_code == 404
    assert c.get("/app/../secret").status_code == 404
