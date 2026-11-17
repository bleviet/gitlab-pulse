"""Tests for the Layer 1 collector orchestrator."""

from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from gitlab.exceptions import GitlabGetError

from app.collector.orchestrator import FAILED_SYNC, SKIPPED_LOCAL_PROJECT, Orchestrator
from app.shared.schemas import RawIssue, RawLabel, RawMilestone


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


class StubRestClient:
    """REST client stub returning a fixed issue list without network access."""

    def __init__(self, issues: list[RawIssue]) -> None:
        self.issues = issues

    def fetch_issues(self, **kwargs: object) -> list[RawIssue]:
        return self.issues

    def fetch_milestones(self, project_id: int) -> list[RawMilestone]:
        return []

    def fetch_labels(self, project_id: int) -> list[RawLabel]:
        return []


def _issue(issue_id: int) -> RawIssue:
    return RawIssue(
        id=issue_id,
        iid=issue_id,
        project_id=7,
        title=f"Issue {issue_id}",
        state="opened",
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
        updated_at=datetime(2025, 1, 2, tzinfo=UTC),
    )


def _orchestrator_with(
    tmp_path: Path, existing: list[int], returned: list[int]
) -> Orchestrator:
    orchestrator = Orchestrator(private_token="test-token", data_path=tmp_path)
    orchestrator._persist_processed(7, [_issue(i) for i in existing])
    stub = StubRestClient([_issue(i) for i in returned])
    orchestrator.rest_client = stub  # type: ignore[assignment]
    orchestrator.gql_client.fetch_hierarchy = lambda *a, **k: {}  # type: ignore[method-assign]
    return orchestrator


def _stored_ids(tmp_path: Path) -> list[int]:
    df = pd.read_parquet(tmp_path / "processed" / "issues_7.parquet")
    return sorted(df["id"].tolist())


def test_full_sync_drops_issue_no_longer_returned(tmp_path: Path) -> None:
    """A full sync replaces the stored issues with the returned set."""
    orchestrator = _orchestrator_with(tmp_path, existing=[1, 2], returned=[1])

    orchestrator.sync_project(7, project_path="g/p", full_sync=True)

    assert _stored_ids(tmp_path) == [1]


def test_incremental_sync_keeps_issues_not_in_batch(tmp_path: Path) -> None:
    """An incremental sync upserts into the stored issues."""
    orchestrator = _orchestrator_with(tmp_path, existing=[1, 2], returned=[1])

    orchestrator.sync_project(7, project_path="g/p")

    assert _stored_ids(tmp_path) == [1, 2]


def test_full_sync_with_no_issues_deletes_parquet(tmp_path: Path) -> None:
    """A full sync that returns nothing removes the project's issue file."""
    orchestrator = _orchestrator_with(tmp_path, existing=[1, 2], returned=[])

    count = orchestrator.sync_project(7, project_path="g/p", full_sync=True)

    assert count == 0
    assert not (tmp_path / "processed" / "issues_7.parquet").exists()


def test_incremental_sync_with_no_issues_keeps_parquet(tmp_path: Path) -> None:
    """An incremental sync that returns nothing leaves the stored issues."""
    orchestrator = _orchestrator_with(tmp_path, existing=[1, 2], returned=[])

    count = orchestrator.sync_project(7, project_path="g/p")

    assert count == 0
    assert _stored_ids(tmp_path) == [1, 2]
