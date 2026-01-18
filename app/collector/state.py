"""Sync state manager for incremental data collection.

Tracks last_updated_at timestamps per project.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ProjectState(BaseModel):
    """State for a single project."""

    project_id: int
    last_updated_at: Optional[datetime] = None
    last_sync_at: Optional[datetime] = None
    issue_count: int = 0


class SyncState(BaseModel):
    """Global sync state across all projects."""

    projects: dict[int, ProjectState] = {}
    version: str = "1.0"


class StateManager:
    """Manages incremental sync state for data collection.

    Persists state to data/state/sync_state.json.
    """

    def __init__(self, state_path: Path = Path("data/state/sync_state.json")) -> None:
        """Initialize the state manager.

        Args:
            state_path: Path to the state JSON file
        """
        self.state_path = state_path
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self._state: Optional[SyncState] = None

    @property
    def state(self) -> SyncState:
        """Get the current sync state, loading from disk if needed."""
        if self._state is None:
            self._state = self._load()
        return self._state

    def get_last_updated(self, project_id: int) -> Optional[datetime]:
        """Get the last_updated_at timestamp for a project.

        Args:
            project_id: GitLab project ID

        Returns:
            Last update timestamp or None for initial sync
        """
        project_state = self.state.projects.get(project_id)
        if project_state:
            return project_state.last_updated_at
        return None

    def get_tracked_projects(self) -> list[int]:
        """Get all project IDs that have been synced before.

        Returns:
            List of project IDs from the state file
        """
        return list(self.state.projects.keys())

    def update_project(
        self,
        project_id: int,
        last_updated_at: datetime,
        issue_count: int,
    ) -> None:
        """Update the state for a project after successful sync.

        Args:
            project_id: GitLab project ID
            last_updated_at: Latest issue update timestamp
            issue_count: Number of issues synced
        """
        self.state.projects[project_id] = ProjectState(
            project_id=project_id,
            last_updated_at=last_updated_at,
            last_sync_at=datetime.now(),
            issue_count=issue_count,
        )
        self._save()

    def _load(self) -> SyncState:
        """Load state from disk."""
        if not self.state_path.exists():
            logger.info("No existing state file, starting fresh")
            return SyncState()

        try:
            with self.state_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return SyncState.model_validate(data)
        except Exception as e:
            logger.warning(f"Failed to load state file: {e}, starting fresh")
            return SyncState()

    def _save(self) -> None:
        """Save state to disk atomically."""
        tmp_path = self.state_path.with_suffix(".tmp")
        try:
            with tmp_path.open("w", encoding="utf-8") as f:
                json.dump(self.state.model_dump(mode="json"), f, indent=2, default=str)
            tmp_path.replace(self.state_path)
            logger.debug(f"State saved to {self.state_path}")
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
            if tmp_path.exists():
                tmp_path.unlink()
            raise
