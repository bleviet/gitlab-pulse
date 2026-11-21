"""Integration tests for the FastAPI Layer 3 dashboard API."""

import struct
import subprocess
from pathlib import Path

import pandas as pd
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


def test_preview_requires_login_and_known_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, _ = _rules_client(tmp_path, monkeypatch)
    item = client.get("/api/rules").json()["rule_sets"][0]
    payload = {"rule": item["rule"]}

    assert client.post("/api/admin/rules/default/preview", json=payload).status_code == 401
    _login(client)
    assert client.post("/api/admin/rules/nope/preview", json=payload).status_code == 404
    assert client.post("/api/admin/rules/..%5Cx/preview", json=payload).status_code in (404, 422)


def test_preview_invalid_draft_returns_problems_without_impact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, _ = _rules_client(tmp_path, monkeypatch)
    _login(client)
    rule = client.get("/api/rules").json()["rule_sets"][0]["rule"]
    rule["classification"][0]["values"][0]["labels"] = ["regex:("]

    res = client.post("/api/admin/rules/default/preview", json={"rule": rule})

    assert res.status_code == 200
    body = res.json()
    assert [p["path"] for p in body["problems"]] == ["classification.priority.0.labels.0"]
    assert body["impact"] is None


def test_preview_valid_draft_returns_impact_and_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "secret-pass")
    template = tmp_path / "template"
    user = tmp_path / "user"
    template.mkdir()
    template.joinpath("default.yaml").write_text(
        "team: default\nworkflow:\n  stages:\n    - name: Review\n", encoding="utf-8"
    )
    before = template.joinpath("default.yaml").read_bytes()
    service = DashboardService(
        analytics_path=tmp_path / "analytics",
        processed_path=tmp_path / "processed",
        state_path=tmp_path / "state.json",
        rules_path=template,
    )
    client = TestClient(
        create_app(
            service=service,
            frontend_dist=tmp_path / "missing_dist",
            rule_store=RuleStore(user_path=user, template_path=template),
        )
    )
    _login(client)
    rule = client.get("/api/rules").json()["rule_sets"][0]["rule"]

    res = client.post("/api/admin/rules/default/preview", json={"rule": rule})

    assert res.status_code == 200
    body = res.json()
    assert body["problems"] == []
    assert body["impact"]["total_issues"] == 0
    assert body["impact"]["project_ids"] == []
    assert template.joinpath("default.yaml").read_bytes() == before
    assert not user.exists()


def test_preview_conflicting_rule_files_return_409(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, rules_dir = _rules_client(tmp_path, monkeypatch)
    for file_name in ("p_a.yaml", "p_b.yaml"):
        rules_dir.joinpath(file_name).write_text("project_ids: [5]\n", encoding="utf-8")
    pd.DataFrame({"id": [1]}).to_parquet(tmp_path / "processed" / "issues_101.parquet")
    _login(client)
    rule = next(
        i for i in client.get("/api/rules").json()["rule_sets"] if i["name"] == "default"
    )["rule"]

    res = client.post("/api/admin/rules/default/preview", json={"rule": rule})

    assert res.status_code == 409
    assert "Two rule files claim the same project" in res.json()["detail"]


def test_preview_skips_work_when_client_disconnected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, _ = _rules_client(tmp_path, monkeypatch)
    _login(client)
    rule = client.get("/api/rules").json()["rule_sets"][0]["rule"]

    async def disconnected(_self: object) -> bool:
        return True

    def fail(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("summarize_impact must not run")

    monkeypatch.setattr("starlette.requests.Request.is_disconnected", disconnected)
    monkeypatch.setattr("app.dashboard.rules_api.summarize_impact", fail)

    res = client.post("/api/admin/rules/default/preview", json={"rule": rule})

    assert res.status_code == 200
    assert res.json()["impact"] is None


def _new_rule(rule: dict[str, object], team: str, project_ids: list[int]) -> dict[str, object]:
    return {**rule, "team": team, "project_ids": project_ids}


def test_create_rule_set(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []
    client, rules_dir = _rules_client(tmp_path, monkeypatch, calls)
    base = client.get("/api/rules").json()["rule_sets"][0]["rule"]

    assert client.post(
        "/api/admin/rules", json={"rule": _new_rule(base, "Backend Team", [7])}
    ).status_code == 401
    _login(client)

    res = client.post(
        "/api/admin/rules", json={"rule": _new_rule(base, "Backend Team", [7])}
    )
    assert res.status_code == 200
    assert res.json()["rule_set"]["name"] == "backend-team"
    assert res.json()["job"]["success"] is True
    assert any("app/processor/main.py" in cmd for cmd in calls)
    assert rules_dir.joinpath("backend-team.yaml").is_file()
    names = [i["name"] for i in client.get("/api/rules").json()["rule_sets"]]
    assert names == ["backend-team", "default"]

    second = client.post(
        "/api/admin/rules", json={"rule": _new_rule(base, "Backend Team", [8])}
    )
    assert second.status_code == 200
    assert second.json()["rule_set"]["name"] == "backend-team-2"


def test_create_rule_set_validates_projects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, _ = _rules_client(tmp_path, monkeypatch)
    _login(client)
    base = client.get("/api/rules").json()["rule_sets"][0]["rule"]
    assert client.post(
        "/api/admin/rules", json={"rule": _new_rule(base, "A", [7])}
    ).status_code == 200

    claimed = client.post("/api/admin/rules", json={"rule": _new_rule(base, "B", [7])})
    assert claimed.status_code == 422
    assert [p["path"] for p in claimed.json()["detail"]["problems"]] == ["project_ids"]

    second_default = client.post("/api/admin/rules", json={"rule": _new_rule(base, "C", [])})
    assert second_default.status_code == 422
    assert [p["path"] for p in second_default.json()["detail"]["problems"]] == ["project_ids"]

    no_team = client.post("/api/admin/rules", json={"rule": _new_rule(base, " ", [9])})
    assert no_team.status_code == 422
    assert [p["path"] for p in no_team.json()["detail"]["problems"]] == ["team"]


def test_delete_rule_set(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []
    client, rules_dir = _rules_client(tmp_path, monkeypatch, calls)
    base = client.get("/api/rules").json()["rule_sets"][0]
    created = client.post(
        "/api/admin/rules", json={"rule": _new_rule(base["rule"], "Temp", [7])}
    )
    assert created.status_code == 401
    _login(client)
    created = client.post(
        "/api/admin/rules", json={"rule": _new_rule(base["rule"], "Temp", [7])}
    ).json()["rule_set"]
    calls.clear()

    url = "/api/admin/rules/temp"
    client.cookies.clear()
    assert client.delete(url, params={"revision": created["revision"]}).status_code == 401
    _login(client)

    default = client.delete("/api/admin/rules/default", params={"revision": base["revision"]})
    assert default.status_code == 422
    assert default.json()["detail"] == (
        "The rule set that applies to all other projects cannot be deleted."
    )
    assert client.delete(url, params={"revision": "stale"}).status_code == 409
    assert client.delete("/api/admin/rules/nope", params={"revision": "x"}).status_code == 404

    ok = client.delete(url, params={"revision": created["revision"]})
    assert ok.status_code == 200
    assert ok.json()["job"]["success"] is True
    assert any("app/processor/main.py" in cmd for cmd in calls)
    assert not rules_dir.joinpath("temp.yaml").exists()
    assert len(list((rules_dir / ".history").glob("temp-*.yaml"))) == 1


def test_rule_versions(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "secret-pass")
    template = tmp_path / "template"
    user = tmp_path / "user"
    template.mkdir()
    template.joinpath("default.yaml").write_text(
        "team: shipped\nworkflow:\n  stages:\n    - name: Review\n", encoding="utf-8"
    )
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
    assert client.get("/api/admin/rules/default/versions").status_code == 401
    _login(client)
    item = client.get("/api/rules").json()["rule_sets"][0]
    for team in ("one", "two"):
        rule = {**item["rule"], "team": team}
        res = client.put(
            "/api/admin/rules/default", json={"revision": item["revision"], "rule": rule}
        )
        assert res.status_code == 200
        item = res.json()["rule_set"]

    versions = client.get("/api/admin/rules/default/versions").json()["versions"]
    assert [v["kind"] for v in versions] == ["history", "history", "template"]
    assert versions[0]["id"] > versions[1]["id"]
    assert versions[0]["saved_at"].endswith("+00:00") and versions[2]["saved_at"] is None
    assert client.get("/api/admin/rules/nope/versions").status_code == 404

    newest = client.get(f"/api/admin/rules/default/versions/{versions[0]['id']}")
    assert newest.json()["rule"]["team"] == "one"
    oldest = client.get(f"/api/admin/rules/default/versions/{versions[1]['id']}")
    assert oldest.json()["rule"]["team"] == "shipped"
    shipped = client.get("/api/admin/rules/default/versions/template")
    assert shipped.json()["rule"]["team"] == "shipped"
    assert client.get("/api/admin/rules/default/versions/not-an-id").status_code == 404
    assert client.get("/api/admin/rules/nope/versions/template").status_code == 404
    history_dir = user / ".history"
    broken = next(history_dir.glob("default-*.yaml"))
    broken.write_text("team: [unclosed\n", encoding="utf-8")
    unreadable = client.get(f"/api/admin/rules/default/versions/{broken.stem[len('default-'):]}")
    assert unreadable.status_code == 422
    assert unreadable.json()["detail"] == "This version cannot be read."


def test_default_name_and_deleting_extra_defaults(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, rules_dir = _rules_client(tmp_path, monkeypatch)
    assert client.get("/api/rules").json()["default_name"] == "default"
    rules_dir.joinpath("zeta.yaml").write_text("team: zeta\n", encoding="utf-8")
    body = client.get("/api/rules").json()
    assert body["default_name"] == "default"
    revisions = {i["name"]: i["revision"] for i in body["rule_sets"]}
    _login(client)

    effective = client.delete(
        "/api/admin/rules/default", params={"revision": revisions["default"]}
    )
    assert effective.status_code == 422
    assert "cannot be deleted" in effective.json()["detail"]

    extra = client.delete("/api/admin/rules/zeta", params={"revision": revisions["zeta"]})
    assert extra.status_code == 200
    assert not rules_dir.joinpath("zeta.yaml").exists()


def test_default_name_is_none_without_default_and_last_set_is_protected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, rules_dir = _rules_client(tmp_path, monkeypatch)
    rules_dir.joinpath("default.yaml").write_text(
        "team: only\nproject_ids: [3]\n", encoding="utf-8"
    )
    body = client.get("/api/rules").json()
    assert body["default_name"] is None
    _login(client)

    res = client.delete(
        "/api/admin/rules/default", params={"revision": body["rule_sets"][0]["revision"]}
    )

    assert res.status_code == 422
    assert res.json()["detail"] == "The last rule set cannot be deleted."
    assert rules_dir.joinpath("default.yaml").is_file()
