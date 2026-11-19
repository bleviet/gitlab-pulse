"""Integration tests for the FastAPI Layer 3 dashboard API."""

import struct
import subprocess
from pathlib import Path

from fastapi.testclient import TestClient

from app.dashboard.server import create_app
from app.dashboard.service import DashboardService
from tests.test_dashboard_service import _write_fixture_data


def test_health_and_empty_dashboard_payload(tmp_path: Path) -> None:
    service = DashboardService(
        analytics_path=tmp_path / "analytics",
        processed_path=tmp_path / "processed",
        state_path=tmp_path / "state" / "sync_state.json",
        rules_path=tmp_path / "rules",
    )
    app = create_app(service=service, frontend_dist=tmp_path / "missing_dist")
    client = TestClient(app)

    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}

    dash = client.get("/api/dashboard")
    assert dash.status_code == 200
    data = dash.json()
    assert data["issues"] == []
    assert data["sync_status"]["status"] == "No sync data"


def test_dashboard_endpoint_serves_parquet_data(tmp_path: Path) -> None:
    analytics_dir, processed_dir, state_file, rules_dir = _write_fixture_data(tmp_path)
    service = DashboardService(
        analytics_path=analytics_dir,
        processed_path=processed_dir,
        state_path=state_file,
        rules_path=rules_dir,
    )
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    dist_dir.joinpath("index.html").write_text("<html><body><div id='root'></div></body></html>", encoding="utf-8")

    app = create_app(service=service, frontend_dist=dist_dir)
    client = TestClient(app)

    res = client.get("/api/dashboard")
    assert res.status_code == 200
    body = res.json()
    assert len(body["issues"]) == 2
    assert body["issues"][0]["contexts"] == ["project::A", "project::B"]

    root = client.get("/")
    assert root.status_code == 200
    assert "<div id='root'>" in root.text

    missing_api = client.get("/api/does-not-exist")
    assert missing_api.status_code == 404


def test_admin_auth_and_operations(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "secret-pass")
    service = DashboardService(
        analytics_path=tmp_path / "analytics",
        processed_path=tmp_path / "processed",
        state_path=tmp_path / "state" / "sync_state.json",
        rules_path=tmp_path / "rules",
    )
    app = create_app(service=service, frontend_dist=tmp_path / "missing_dist")
    client = TestClient(app)

    assert client.get("/api/admin/status").json() == {"authenticated": False}
    assert client.post("/api/admin/clear-cache").status_code == 401
    assert client.post("/api/admin/login", json={"password": "wrong"}).status_code == 401

    login_res = client.post("/api/admin/login", json={"password": "secret-pass"})
    assert login_res.status_code == 200
    assert login_res.json() == {"authenticated": True}
    assert client.get("/api/admin/status").json() == {"authenticated": True}

    cache_res = client.post("/api/admin/clear-cache")
    assert cache_res.status_code == 200
    assert cache_res.json() == {"ok": True}

    def fake_run(cmd, **_kwargs):
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout=f"ran {' '.join(cmd)}",
            stderr="",
        )

    monkeypatch.setattr("app.dashboard.admin.subprocess.run", fake_run)
    proc_res = client.post("/api/admin/run/processor")
    assert proc_res.status_code == 200
    assert proc_res.json()["success"] is True
    assert "app/processor/main.py" in proc_res.json()["stdout"]

    logout_res = client.post("/api/admin/logout")
    assert logout_res.status_code == 200
    assert logout_res.json() == {"authenticated": False}
    assert client.post("/api/admin/clear-cache").status_code == 401


def test_favicon_assets_and_missing_icon_do_not_return_html(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    favicon_png = repo_root / "frontend" / "public" / "static" / "favicon.png"
    favicon_32 = repo_root / "frontend" / "public" / "static" / "favicon-32x32.png"
    favicon_ico = repo_root / "frontend" / "public" / "favicon.ico"

    for png_path in (favicon_png, favicon_32):
        assert png_path.is_file()
        png_bytes = png_path.read_bytes()
        assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n"
        bit_depth = struct.unpack(">B", png_bytes[24:25])[0]
        assert bit_depth == 8

    assert favicon_ico.is_file()
    assert favicon_ico.read_bytes()[:4] == b"\x00\x00\x01\x00"

    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    dist_dir.joinpath("index.html").write_text("<html></html>", encoding="utf-8")

    service = DashboardService(
        analytics_path=tmp_path / "analytics",
        processed_path=tmp_path / "processed",
        state_path=tmp_path / "state" / "sync_state.json",
        rules_path=tmp_path / "rules",
    )
    app = create_app(service=service, frontend_dist=dist_dir)
    client = TestClient(app)

    missing_ico = client.get("/favicon.ico")
    assert missing_ico.status_code == 404

    dist_dir.joinpath("favicon.ico").write_bytes(favicon_ico.read_bytes())
    present_ico = client.get("/favicon.ico")
    assert present_ico.status_code == 200
    assert present_ico.headers["content-type"].startswith("image/")
    assert present_ico.headers["cache-control"] == "no-cache"
    assert present_ico.content[:4] == b"\x00\x00\x01\x00"
