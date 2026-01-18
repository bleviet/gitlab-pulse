"""REST API client for GitLab data extraction.

Wraps python-gitlab library with incremental sync support.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import gitlab
from gitlab.v4.objects import ProjectIssue

from app.shared.schemas import RawIssue

logger = logging.getLogger(__name__)


class RestClient:
    """REST API client for GitLab issue extraction.

    Uses python-gitlab for metadata retrieval with incremental sync support.
    Persists raw JSON responses to Layer 0 (data/raw/) for auditing.
    """

    def __init__(
        self,
        gitlab_url: Optional[str] = None,
        private_token: Optional[str] = None,
        raw_data_path: Path = Path("data/raw"),
    ) -> None:
        """Initialize the REST client.

        Args:
            gitlab_url: GitLab instance URL (default: GITLAB_URL env var)
            private_token: GitLab private token (default: GITLAB_TOKEN env var)
            raw_data_path: Path for storing raw JSON responses
        """
        self.gitlab_url = gitlab_url or os.environ.get("GITLAB_URL", "https://gitlab.com")
        self.private_token = private_token or os.environ.get("GITLAB_TOKEN", "")

        if not self.private_token:
            raise ValueError("GITLAB_TOKEN environment variable is required")

        self.gl = gitlab.Gitlab(self.gitlab_url, private_token=self.private_token)
        self.raw_data_path = raw_data_path
        self.raw_data_path.mkdir(parents=True, exist_ok=True)

    def fetch_issues(
        self,
        project_id: int,
        updated_after: Optional[datetime] = None,
        persist_raw: bool = True,
    ) -> list[RawIssue]:
        """Fetch issues from a GitLab project.

        Args:
            project_id: GitLab project ID
            updated_after: Only fetch issues updated after this timestamp
            persist_raw: Whether to save raw JSON to data/raw/

        Returns:
            List of validated RawIssue objects
        """
        project = self.gl.projects.get(project_id)
        logger.info(f"Fetching issues from project {project_id}")

        # Build query parameters
        params: dict[str, Any] = {
            "state": "all",
            "per_page": 100,
            "order_by": "updated_at",
            "sort": "asc",
        }

        if updated_after:
            params["updated_after"] = updated_after.isoformat()
            logger.info(f"Incremental sync: updated_after={updated_after}")

        # Fetch all pages
        raw_issues: list[dict[str, Any]] = []
        issues_list = project.issues.list(iterator=True, **params)

        for issue in issues_list:
            raw_issues.append(self._issue_to_dict(issue))

        logger.info(f"Fetched {len(raw_issues)} issues from project {project_id}")

        # Persist raw JSON (Layer 0)
        if persist_raw and raw_issues:
            self._persist_raw(project_id, raw_issues)

        # Validate and convert to Pydantic models
        validated_issues: list[RawIssue] = []
        for raw in raw_issues:
            try:
                validated_issues.append(RawIssue.model_validate(raw))
            except Exception as e:
                logger.warning(f"Validation error for issue {raw.get('id')}: {e}")

        return validated_issues

    def _issue_to_dict(self, issue: ProjectIssue) -> dict[str, Any]:
        """Convert GitLab issue object to dictionary."""
        attrs = issue.attributes
        return {
            "id": attrs.get("id"),
            "iid": attrs.get("iid"),
            "project_id": attrs.get("project_id"),
            "title": attrs.get("title"),
            "state": attrs.get("state"),
            "created_at": attrs.get("created_at"),
            "updated_at": attrs.get("updated_at"),
            "closed_at": attrs.get("closed_at"),
            "labels": attrs.get("labels", []),
            "web_url": attrs.get("web_url"),
            "assignee": attrs.get("assignee", {}).get("username") if attrs.get("assignee") else None,
            "milestone": attrs.get("milestone", {}).get("title") if attrs.get("milestone") else None,
            "milestone_id": attrs.get("milestone", {}).get("id") if attrs.get("milestone") else None,
            "milestone_due_date": attrs.get("milestone", {}).get("due_date") if attrs.get("milestone") else None,
            "milestone_start_date": attrs.get("milestone", {}).get("start_date") if attrs.get("milestone") else None,
        }

    def get_project_path(self, project_id: int) -> str:
        """Fetch the full project path (namespace/name)."""
        project = self.gl.projects.get(project_id)
        return project.path_with_namespace


    def _persist_raw(self, project_id: int, issues: list[dict[str, Any]]) -> None:
        """Persist raw JSON response to Layer 0.

        Uses atomic write pattern (write to .tmp, then rename).
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{project_id}_{timestamp}.json"
        filepath = self.raw_data_path / filename
        tmp_filepath = filepath.with_suffix(".tmp")

        try:
            with tmp_filepath.open("w", encoding="utf-8") as f:
                json.dump(issues, f, indent=2, default=str)
            tmp_filepath.replace(filepath)
            logger.info(f"Persisted raw data to {filepath}")
        except Exception as e:
            logger.error(f"Failed to persist raw data: {e}")
            if tmp_filepath.exists():
                tmp_filepath.unlink()
            raise
