"""Tests for the Layer 1 collector orchestrator."""

from pathlib import Path

from gitlab.exceptions import GitlabGetError

from app.collector.orchestrator import FAILED_SYNC, SKIPPED_LOCAL_PROJECT, Orchestrator


class MissingProjectOrchestrator(Orchestrator):
    """Test orchestrator that simulates a missing remote project."""

    def sync_project(
        self,
        project_id: int,
        project_path: str | None = None,
        full_sync: bool = False,
    ) -> int:
        del project_id, project_path, full_sync
        raise GitlabGetError("404 Project Not Found", 404)


def test_sync_all_skips_missing_seeded_local_project(
    tmp_path: Path,
) -> None:
    """Skip 404s when local seeded processed data already exists."""
    processed_path = tmp_path / "processed"
    processed_path.mkdir(parents=True, exist_ok=True)
    (processed_path / "issues_101.parquet").touch()

    orchestrator = MissingProjectOrchestrator(
        private_token="test-token",
        data_path=tmp_path,
    )

    results = orchestrator.sync_all(project_ids=[101])

    assert results == {101: SKIPPED_LOCAL_PROJECT}


def test_sync_all_fails_for_missing_remote_project_without_local_data(
    tmp_path: Path,
) -> None:
    """Keep true missing remote projects as failures."""
    orchestrator = MissingProjectOrchestrator(
        private_token="test-token",
        data_path=tmp_path,
    )

    results = orchestrator.sync_all(project_ids=[999])

    assert results == {999: FAILED_SYNC}
