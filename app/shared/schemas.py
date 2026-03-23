"""Shared schemas and data models used across all layers.

This module defines the core data models that are shared between
Layer 1 (Collector), Layer 2 (Processor), and Layer 3 (Dashboard).
"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class RawIssue(BaseModel):
    """Raw issue data from GitLab API (Layer 1 output schema).

    This model represents the normalized union of REST API and GraphQL data.
    It is used for both serialization to Parquet and deserialization in Layer 2.
    """

    id: int = Field(description="GitLab global issue ID")
    iid: int = Field(description="Project-scoped issue ID")
    project_id: int = Field(description="GitLab project ID")
    title: str = Field(description="Issue title")
    state: Literal["opened", "closed"] = Field(description="Issue state")
    created_at: datetime = Field(description="Creation timestamp (UTC)")
    updated_at: datetime = Field(description="Last update timestamp (UTC)")
    closed_at: Optional[datetime] = Field(default=None, description="Closure timestamp")
    labels: list[str] = Field(default_factory=list, description="Issue labels")
    description: Optional[str] = Field(default=None, description="Issue description/body")

    # GraphQL-enriched fields (hierarchy)
    work_item_type: str = Field(default="ISSUE", description="Work item type")
    parent_id: Optional[int] = Field(default=None, description="Parent issue ID")
    child_ids: list[int] = Field(default_factory=list, description="Child issue IDs")

    # Optional metadata
    web_url: Optional[str] = Field(default=None, description="Issue URL")
    assignee: Optional[str] = Field(default=None, description="Assignee username")
    milestone: Optional[str] = Field(default=None, description="Milestone title")
    milestone_id: Optional[int] = Field(default=None, description="Milestone ID")
    milestone_due_date: Optional[datetime] = Field(default=None, description="Milestone due date")
    milestone_start_date: Optional[datetime] = Field(default=None, description="Milestone start date")

    model_config = {"frozen": False, "extra": "ignore"}

    @field_validator("created_at", "updated_at", "closed_at", mode="before")
    @classmethod
    def parse_datetime(cls, v: object) -> Optional[datetime]:
        """Parse ISO datetime strings to datetime objects."""
        if v is None:
            return None
        if isinstance(v, datetime):
            return v
        if isinstance(v, str):
            # Handle ISO format with or without timezone
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        raise ValueError(f"Cannot parse datetime from {type(v)}")


class RawMilestone(BaseModel):
    """Raw milestone data from GitLab API.

    Fetched independently to track milestones without assigned issues.
    """

    id: int = Field(description="GitLab milestone ID")
    iid: int = Field(description="Project-scoped milestone ID")
    project_id: int = Field(description="GitLab project ID")
    title: str = Field(description="Milestone title")
    description: Optional[str] = Field(default=None, description="Description")
    state: Literal["active", "closed"] = Field(description="Milestone state")
    due_date: Optional[datetime] = Field(default=None, description="Due date")
    start_date: Optional[datetime] = Field(default=None, description="Start date")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")
    web_url: Optional[str] = Field(default=None, description="Milestone URL")

    model_config = {"frozen": False, "extra": "ignore"}

    @field_validator("due_date", "start_date", "created_at", "updated_at", mode="before")
    @classmethod
    def parse_date(cls, v: object) -> Optional[datetime]:
        """Parse date strings to datetime objects."""
        if v is None:
            return None
        if isinstance(v, datetime):
            return v
        if isinstance(v, str):
            # Handle both date (YYYY-MM-DD) and datetime formats
            if "T" in v:
                return datetime.fromisoformat(v.replace("Z", "+00:00"))
            return datetime.fromisoformat(v + "T00:00:00+00:00")
        raise ValueError(f"Cannot parse date from {type(v)}")


class RawLabel(BaseModel):
    """Raw label data from GitLab API.

    Used to persist label metadata like colors.
    """

    id: int = Field(description="GitLab label ID")
    name: str = Field(description="Label name")
    color: str = Field(description="Hex color code (e.g. #FF0000)")
    description: Optional[str] = Field(default=None, description="Description")
    project_id: int = Field(description="GitLab project ID")
    text_color: Optional[str] = Field(default="#FFFFFF", description="Text color (calculated by GitLab)")

    model_config = {"frozen": False, "extra": "ignore"}


class AnalyticsIssue(BaseModel):
    """Enriched issue with calculated metrics (Layer 2 output schema).

    Extends RawIssue with computed fields like age_days, cycle_time, etc.
    """

    # Core fields from RawIssue
    id: int
    iid: int
    project_id: int
    title: str
    state: Literal["opened", "closed"]
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime] = None
    labels: list[str] = Field(default_factory=list)
    description: Optional[str] = None
    work_item_type: str = "ISSUE"
    parent_id: Optional[int] = None
    child_ids: list[int] = Field(default_factory=list)
    web_url: Optional[str] = None
    assignee: Optional[str] = None
    milestone: Optional[str] = None
    milestone_id: Optional[int] = None
    milestone_due_date: Optional[datetime] = None
    milestone_start_date: Optional[datetime] = None

    # Enriched fields (Layer 2)
    age_days: int = Field(default=0, description="Days since creation")
    cycle_time: Optional[int] = Field(default=None, description="Days from open to close")
    is_stale: bool = Field(default=False, description="Exceeds staleness threshold")

    # Mapped fields from rules
    issue_type: Optional[str] = Field(default=None, description="Mapped type (Bug, Feature)")
    severity: Optional[str] = Field(default=None, description="Mapped severity level")
    team: Optional[str] = Field(default=None, description="Owning team/domain")

    model_config = {"frozen": False, "extra": "ignore"}


class QualityIssue(BaseModel):
    """Issue with validation hints in the Layer 2 quality output.

    Contains the issue data plus error information for quality-oriented widgets.
    """

    id: int
    iid: int
    project_id: int
    title: str
    state: Literal["opened", "closed"]
    created_at: datetime
    updated_at: datetime
    labels: list[str] = Field(default_factory=list)
    web_url: Optional[str] = None
    assignee: Optional[str] = None

    # Quality metadata
    error_code: str = Field(description="Validation error code")
    error_message: str = Field(description="Human-readable error description")

    model_config = {"frozen": False, "extra": "ignore"}


# Parquet column types for pandas
PARQUET_DTYPES = {
    "id": "int64",
    "iid": "int64",
    "project_id": "int64",
    "title": "string",
    "state": "category",
    "work_item_type": "category",
    "issue_type": "category",
    "severity": "category",
    "team": "category",
    "is_stale": "bool",
    "milestone": "category",
    "milestone_id": "float",  # Nullable int is often float in pandas < 1.0 or w/o Int64
}
