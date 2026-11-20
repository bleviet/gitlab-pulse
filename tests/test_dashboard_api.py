"""Integration tests for the FastAPI Layer 3 dashboard API."""

import struct
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.dashboard.server import create_app
from app.dashboard.service import DashboardService
from app.processor.rule_store import RuleStore
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


def _rules_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, calls: list[list[str]] | None = None
) -> tuple[TestClient, Path]:
    monkeypatch.setenv("ADMIN_PASSWORD", "secret-pass")
    analytics_dir, processed_dir, state_file, rules_dir = _write_fixture_data(tmp_path)
    service = DashboardService(
        analytics_path=analytics_dir,
        processed_path=processed_dir,
        state_path=state_file,
        rules_path=rules_dir,
    )
    template_dir = tmp_path / "template_rules"
    template_dir.mkdir()
    store = RuleStore(user_path=rules_dir, template_path=template_dir)
    client = TestClient(
        create_app(
            service=service,
            frontend_dist=tmp_path / "missing_dist",
            rule_store=store,
        )
    )

    def fake_run(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        if calls is not None:
            calls.append(list(cmd))
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr("app.dashboard.admin.subprocess.run", fake_run)
    return client, rules_dir


def _login(client: TestClient) -> None:
    res = client.post("/api/admin/login", json={"password": "secret-pass"})
    assert res.status_code == 200


def test_get_rules_returns_ordered_lists(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client, _ = _rules_client(tmp_path, monkeypatch)

    res = client.get("/api/rules")

    assert res.status_code == 200
    body = res.json()
    assert body["source"] == "user"
    assert body["load_errors"] == {}
    item = body["rule_sets"][0]
    assert item["name"] == "default"
    assert len(item["revision"]) == 64
    category = item["rule"]["classification"][0]
    assert category["name"] == "priority"
    assert [v["name"] for v in category["values"]] == ["P1", "P2"]
    assert category["values"][0]["labels"] == ["priority::1"]
    assert item["rule"]["workflow"]["stages"][0]["description"] == "Peer review"


def test_put_rules_requires_login(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client, _ = _rules_client(tmp_path, monkeypatch)
    item = client.get("/api/rules").json()["rule_sets"][0]

    res = client.put(
        "/api/admin/rules/default",
        json={"revision": item["revision"], "rule": item["rule"]},
    )

    assert res.status_code == 401


def test_put_rules_saves_runs_processor_and_refreshes_dashboard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[list[str]] = []
    client, rules_dir = _rules_client(tmp_path, monkeypatch, calls)
    _login(client)
    assert client.get("/api/dashboard").json()["stages"][0]["description"] == "Peer review"
    item = client.get("/api/rules").json()["rule_sets"][0]
    rule = item["rule"]
    rule["workflow"]["stages"][0]["description"] = "Second pair of eyes"
    rule["classification"][0]["values"].reverse()

    res = client.put(
        "/api/admin/rules/default", json={"revision": item["revision"], "rule": rule}
    )

    assert res.status_code == 200
    body = res.json()
    assert body["job"]["success"] is True
    assert body["rule_set"]["revision"] != item["revision"]
    assert any("app/processor/main.py" in cmd for cmd in calls)
    text = rules_dir.joinpath("default.yaml").read_text(encoding="utf-8")
    assert "Second pair of eyes" in text
    assert text.index("P2:") < text.index("P1:")
    assert (
        client.get("/api/dashboard").json()["stages"][0]["description"]
        == "Second pair of eyes"
    )


def test_put_rules_stale_revision_conflicts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client, _ = _rules_client(tmp_path, monkeypatch)
    _login(client)
    item = client.get("/api/rules").json()["rule_sets"][0]

    res = client.put(
        "/api/admin/rules/default", json={"revision": "stale", "rule": item["rule"]}
    )

    assert res.status_code == 409
    assert "Reload" in res.json()["detail"]


def test_put_rules_invalid_body_lists_problems(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client, rules_dir = _rules_client(tmp_path, monkeypatch)
    _login(client)
    item = client.get("/api/rules").json()["rule_sets"][0]
    before = rules_dir.joinpath("default.yaml").read_bytes()
    rule = item["rule"]
    rule["workflow"]["stages"][0]["name"] = ""
    rule["classification"][0]["values"][0]["labels"] = ["regex:("]

    res = client.put(
        "/api/admin/rules/default", json={"revision": item["revision"], "rule": rule}
    )

    assert res.status_code == 422
    detail = res.json()["detail"]
    assert detail["message"] == "2 problems need fixing before these rules can be saved."
    assert {p["path"] for p in detail["problems"]} == {
        "workflow.stages.0.name",
        "classification.priority.0.labels.0",
    }
    assert rules_dir.joinpath("default.yaml").read_bytes() == before


def test_put_rules_unknown_name_not_found(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client, _ = _rules_client(tmp_path, monkeypatch)
    _login(client)
    item = client.get("/api/rules").json()["rule_sets"][0]

    res = client.put(
        "/api/admin/rules/nope", json={"revision": item["revision"], "rule": item["rule"]}
    )

    assert res.status_code == 404


def test_put_rules_duplicate_classification_values_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, _ = _rules_client(tmp_path, monkeypatch)
    _login(client)
    item = client.get("/api/rules").json()["rule_sets"][0]
    rule = item["rule"]
    rule["classification"][0]["values"][1]["name"] = "P1"

    res = client.put(
        "/api/admin/rules/default", json={"revision": item["revision"], "rule": rule}
    )

    assert res.status_code == 422
    paths = [p["path"] for p in res.json()["detail"]["problems"]]
    assert paths == ["classification.priority.1.name"]


def test_put_rules_duplicate_names_skip_other_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, _ = _rules_client(tmp_path, monkeypatch)
    _login(client)
    item = client.get("/api/rules").json()["rule_sets"][0]
    rule = item["rule"]
    rule["classification"] = [
        {
            "name": "type",
            "values": [
                {"name": "A", "labels": [], "title": []},
                {"name": "B", "labels": [], "title": []},
                {"name": "A", "labels": [], "title": []},
                {"name": "C", "labels": ["regex:("], "title": []},
            ],
        }
    ]

    res = client.put(
        "/api/admin/rules/default", json={"revision": item["revision"], "rule": rule}
    )

    assert res.status_code == 422
    detail = res.json()["detail"]
    assert detail["message"] == "1 problem needs fixing before these rules can be saved."
    assert [p["path"] for p in detail["problems"]] == ["classification.type.2.name"]


def test_put_rules_existing_project_conflict_does_not_block_edit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, rules_dir = _rules_client(tmp_path, monkeypatch)
    rules_dir.joinpath("second.yaml").write_text("team: second\n", encoding="utf-8")
    _login(client)
    item = next(
        i for i in client.get("/api/rules").json()["rule_sets"] if i["name"] == "default"
    )
    rule = item["rule"]
    rule["workflow"]["stages"][0]["description"] = "Edited"

    ok = client.put(
        "/api/admin/rules/default", json={"revision": item["revision"], "rule": rule}
    )
    assert ok.status_code == 200

    item = next(
        i for i in client.get("/api/rules").json()["rule_sets"] if i["name"] == "default"
    )
    rule = item["rule"]
    rule["project_ids"] = [5]
    rules_dir.joinpath("second.yaml").write_text(
        "project_ids: [5]\nteam: second\n", encoding="utf-8"
    )
    bad = client.put(
        "/api/admin/rules/default", json={"revision": item["revision"], "rule": rule}
    )
    assert bad.status_code == 422
    assert [p["path"] for p in bad.json()["detail"]["problems"]] == ["project_ids"]


def test_first_save_from_template_seeds_user_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "secret-pass")
    template = tmp_path / "template"
    user = tmp_path / "user"
    template.mkdir()
    template.joinpath("default.yaml").write_text(
        "team: default\nworkflow:\n  stages:\n    - name: Review\n", encoding="utf-8"
    )
    template.joinpath("other.yaml").write_text("project_ids: [5]\n", encoding="utf-8")
    before = template.joinpath("default.yaml").read_bytes()
    service = DashboardService(
        analytics_path=tmp_path / "analytics",
        processed_path=tmp_path / "processed",
        state_path=tmp_path / "state.json",
        rules_path=user,
    )
    client = TestClient(
        create_app(
            service=service,
            frontend_dist=tmp_path / "missing_dist",
            rule_store=RuleStore(user_path=user, template_path=template),
        )
    )
    monkeypatch.setattr(
        "app.dashboard.admin.subprocess.run",
        lambda cmd, **_kw: subprocess.CompletedProcess(cmd, 0, "ok", ""),
    )
    _login(client)
    first = client.get("/api/rules").json()
    assert first["source"] == "template"
    item = first["rule_sets"][0]

    res = client.put(
        "/api/admin/rules/default", json={"revision": item["revision"], "rule": item["rule"]}
    )

    assert res.status_code == 200
    assert client.get("/api/rules").json()["source"] == "user"
    assert template.joinpath("default.yaml").read_bytes() == before
    assert user.joinpath("default.yaml").is_file()
    assert user.joinpath("other.yaml").is_file()
    assert list(user.glob("*.tmp")) == []


def test_get_rules_reports_malformed_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, rules_dir = _rules_client(tmp_path, monkeypatch)
    rules_dir.joinpath("broken.yaml").write_text("project_ids: [unclosed\n", encoding="utf-8")

    body = client.get("/api/rules").json()

    assert [i["name"] for i in body["rule_sets"]] == ["default"]
    assert list(body["load_errors"]) == ["broken.yaml"]
