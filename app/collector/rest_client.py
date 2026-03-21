"""REST API client for GitLab data extraction.

Wraps python-gitlab library with incremental sync support.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import gitlab
from gitlab.v4.objects import ProjectIssue

from app.shared.schemas import RawIssue, RawMilestone

logger = logging.getLogger(__name__)


class RestClient:
    """REST API client for GitLab issue extraction.

    Uses python-gitlab for metadata retrieval with incremental sync support.
    Persists raw JSON responses to Layer 0 (data/raw/) for auditing.
    """

    def __init__(
        self,
        gitlab_url: str | None = None,
        private_token: str | None = None,
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
        updated_after: datetime | None = None,
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
            # Add 1 second to make the filter exclusive (GitLab uses >=)
            from datetime import timedelta
            exclusive_after = updated_after + timedelta(seconds=1)
            params["updated_after"] = exclusive_after.isoformat()
            logger.info(f"Incremental sync: updated_after={exclusive_after}")

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
            "description": attrs.get("description"),
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
        return str(project.path_with_namespace)

    def fetch_milestones(self, project_id: int) -> list[RawMilestone]:
        """Fetch all milestones from a GitLab project.

        Args:
            project_id: GitLab project ID

        Returns:
            List of validated RawMilestone objects
        """
        project = self.gl.projects.get(project_id)
        logger.info(f"Fetching milestones from project {project_id}")

        # Fetch all milestones (both active and closed)
        raw_milestones: list[dict[str, Any]] = []
        for state in ["active", "closed"]:
            milestones_list = project.milestones.list(state=state, iterator=True)
            for ms in milestones_list:
                raw_milestones.append({
                    "id": ms.id,
                    "iid": ms.iid,
                    "project_id": project_id,
                    "title": ms.title,
                    "description": ms.description,
                    "state": ms.state,
                    "due_date": ms.due_date,
                    "start_date": ms.start_date,
                    "created_at": ms.created_at,
                    "updated_at": ms.updated_at,
                    "web_url": ms.web_url,
                })

        logger.info(f"Fetched {len(raw_milestones)} milestones from project {project_id}")

        # Validate and convert to Pydantic models
        validated: list[RawMilestone] = []
        for raw in raw_milestones:
            try:
                validated.append(RawMilestone.model_validate(raw))
            except Exception as e:
                logger.warning(f"Validation error for milestone {raw.get('id')}: {e}")

        return validated

    def fetch_labels(self, project_id: int) -> list[Any]:
        """Fetch all labels from a GitLab project.

        Args:
            project_id: GitLab project ID

        Returns:
            List of validated RawLabel objects (returned as Any to avoid circular imports if strict typing issues arise, but effectively RawLabel)
        """
        from app.shared.schemas import RawLabel

        project = self.gl.projects.get(project_id)
        logger.info(f"Fetching labels from project {project_id}")

        raw_labels = project.labels.list(iterator=True)

        validated: list[RawLabel] = []
        for label in raw_labels:
            try:
                # python-gitlab label objects have attributes accessible
                attrs = label.attributes
                validated.append(RawLabel(
                    id=attrs["id"],
                    name=attrs["name"],
                    color=attrs["color"],
                    description=attrs.get("description"),
                    project_id=project_id,
                    text_color=attrs.get("text_color", "#FFFFFF")
                ))
            except Exception as e:
                logger.warning(f"Validation error for label {getattr(label, 'name', 'unknown')}: {e}")

        logger.info(f"Fetched {len(validated)} labels from project {project_id}")
        return validated


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
