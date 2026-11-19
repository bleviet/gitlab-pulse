"""Tests for the static demo payload exporter."""

from pathlib import Path

from app.dashboard.schemas import DashboardPayload
from app.dashboard.service import DashboardService
from tests.test_dashboard_service import _write_fixture_data
from tools.export_demo_payload import export_payload


def test_export_payload_writes_parseable_json_without_tmp_file(tmp_path: Path) -> None:
    analytics_dir, processed_dir, state_file, rules_dir = _write_fixture_data(tmp_path)
    service = DashboardService(
        analytics_path=analytics_dir,
        processed_path=processed_dir,
        state_path=state_file,
        rules_path=rules_dir,
    )
    output = tmp_path / "out" / "demo-data" / "dashboard.json"

    written = export_payload(service, output)

    assert written == output
    payload = DashboardPayload.model_validate_json(output.read_text(encoding="utf-8"))
    assert len(payload.issues) == 2
    assert list(output.parent.glob("*.tmp")) == []
