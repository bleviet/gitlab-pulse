"""Ingestion Orchestrator for Layer 1 Data Acquisition.

Coordinates the full sync pipeline: REST → Raw → GraphQL → Transform → Parquet.
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from app.collector.gql_client import GqlClient
from app.collector.rest_client import RestClient
from app.collector.state import StateManager
from app.shared.schemas import RawIssue

logger = logging.getLogger(__name__)


class Orchestrator:
    """Ingestion orchestrator for the hybrid collector.

    Implements the sync algorithm:
    1. Check State → 2. Fetch REST → 3. Persist L0 → 4. Enrich GQL → 5. Transform → 6. Persist L1
    """

    def __init__(
        self,
        gitlab_url: Optional[str] = None,
        private_token: Optional[str] = None,
        data_path: Path = Path("data"),
    ) -> None:
        """Initialize the orchestrator.

        Args:
            gitlab_url: GitLab instance URL
            private_token: GitLab private token
            data_path: Base path for data storage
        """
        self.rest_client = RestClient(
            gitlab_url=gitlab_url,
            private_token=private_token,
            raw_data_path=data_path / "raw",
        )
        self.gql_client = GqlClient(
            gitlab_url=gitlab_url,
            private_token=private_token,
        )
        self.state_manager = StateManager(
            state_path=data_path / "state" / "sync_state.json"
        )
        self.processed_path = data_path / "processed"
        self.processed_path.mkdir(parents=True, exist_ok=True)

    def sync_project(
        self,
        project_id: int,
        project_path: Optional[str] = None,
        full_sync: bool = False,
    ) -> int:
        """Sync issues from a single GitLab project.

        Args:
            project_id: GitLab project ID
            project_path: Full project path for GraphQL (e.g., "group/project")
            full_sync: If True, ignore incremental state and sync all issues

        Returns:
            Number of issues synced
        """
        logger.info(f"Starting sync for project {project_id}")

        # Step 1: Check State
        updated_after = None if full_sync else self.state_manager.get_last_updated(project_id)

        # Step 2 & 3: Fetch REST (also persists L0)
        issues = self.rest_client.fetch_issues(
            project_id=project_id,
            updated_after=updated_after,
            persist_raw=True,
        )

        if not issues:
            logger.info(f"No new issues found for project {project_id}")
            return 0

        # Step 4: Enrich with GraphQL (hierarchy)
        if project_path:
            iids = [issue.iid for issue in issues]
            hierarchy = self.gql_client.fetch_hierarchy(project_path, iids)

            for issue in issues:
                if issue.iid in hierarchy:
                    h = hierarchy[issue.iid]
                    issue.work_item_type = h.get("work_item_type", "ISSUE")
                    issue.parent_id = h.get("parent_id")
                    issue.child_ids = h.get("child_ids", [])

        # Step 5 & 6: Transform and Persist L1
        self._persist_processed(project_id, issues)

        # Update state
        max_updated = max(issue.updated_at for issue in issues)
        self.state_manager.update_project(
            project_id=project_id,
            last_updated_at=max_updated,
            issue_count=len(issues),
        )

        logger.info(f"Synced {len(issues)} issues for project {project_id}")
        return len(issues)

    def sync_all(
        self,
        project_ids: Optional[list[int]] = None,
        full_sync: bool = False,
    ) -> dict[int, int]:
        """Sync issues from multiple projects.

        Args:
            project_ids: List of project IDs (default: from PROJECT_IDS env var)
            full_sync: If True, ignore incremental state

        Returns:
            Dict mapping project_id to issue count
        """
        if project_ids is None:
            env_projects = os.environ.get("PROJECT_IDS", "")
            if not env_projects:
                raise ValueError("PROJECT_IDS environment variable is required")
            project_ids = [int(p.strip()) for p in env_projects.split(",")]

        results: dict[int, int] = {}
        for project_id in project_ids:
            try:
                count = self.sync_project(project_id, full_sync=full_sync)
                results[project_id] = count
            except Exception as e:
                logger.error(f"Failed to sync project {project_id}: {e}")
                results[project_id] = -1

        return results

    def _persist_processed(self, project_id: int, issues: list[RawIssue]) -> None:
        """Persist validated issues to Parquet (Layer 1 output).

        Uses upsert logic to merge with existing data.
        """
        filepath = self.processed_path / f"issues_{project_id}.parquet"

        # Convert to DataFrame
        new_df = pd.DataFrame([issue.model_dump() for issue in issues])

        # Merge with existing data (upsert on id)
        if filepath.exists():
            existing_df = pd.read_parquet(filepath)
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            combined_df = combined_df.drop_duplicates(subset=["id"], keep="last")
        else:
            combined_df = new_df

        # Atomic write
        tmp_filepath = filepath.with_suffix(".tmp")
        combined_df.to_parquet(tmp_filepath, engine="pyarrow", compression="snappy")
        tmp_filepath.replace(filepath)

        logger.info(f"Persisted {len(issues)} issues to {filepath}")


def main() -> None:
    """CLI entry point for the collector."""
    import argparse
    from dotenv import load_dotenv

    load_dotenv()


    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    parser = argparse.ArgumentParser(description="GitLabInsight Data Collector")
    parser.add_argument("--project-ids", type=str, help="Comma-separated project IDs")
    parser.add_argument("--full-sync", action="store_true", help="Ignore incremental state")
    parser.add_argument("--data-path", type=str, default="data", help="Data directory path")
    args = parser.parse_args()

    orchestrator = Orchestrator(data_path=Path(args.data_path))

    project_ids = None
    if args.project_ids:
        project_ids = [int(p.strip()) for p in args.project_ids.split(",")]

    results = orchestrator.sync_all(project_ids=project_ids, full_sync=args.full_sync)

    print("\nSync Results:")
    for project_id, count in results.items():
        status = f"{count} issues" if count >= 0 else "FAILED"
        print(f"  Project {project_id}: {status}")


if __name__ == "__main__":
    main()
