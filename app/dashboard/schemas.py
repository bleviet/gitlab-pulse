"""Pydantic v2 response and request schemas for the dashboard API."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class IssueItem(BaseModel):
    """Single deduplicated issue prepared for the Layer 3 SPA."""

    model_config = ConfigDict(frozen=True)

    id: int
    iid: int
    project_id: int
    title: str
    state: Literal["opened", "closed"]
    created_at: str
    updated_at: str
    closed_at: str | None = None
    labels: list[str] = Field(default_factory=list)
    contexts: list[str] = Field(default_factory=list)
    work_item_type: str = "ISSUE"
    parent_id: int | None = None
    child_ids: list[int] = Field(default_factory=list)
    web_url: str | None = None
    assignee: str = "Unassigned"
    milestone: str | None = None
    milestone_id: int | None = None
    milestone_due_date: str | None = None
    milestone_start_date: str | None = None
    age_days: int = 0
    cycle_time: int | None = None
    is_stale: bool = False
    issue_type: str | None = None
    severity: str | None = None
    priority: str = "Unset"
    priority_rank: int | None = None
    team: str | None = None
    stage: str = "Backlog"
    stage_type: str | None = None
    stage_order: int = 999
    days_in_stage: int = 0
    quality_signals: list[str] = Field(default_factory=list)
    quality_hints: list[str] = Field(default_factory=list)


class LabelStyle(BaseModel):
    """Visual color styling for a GitLab label."""

    model_config = ConfigDict(frozen=True)

    color: str
    text_color: str


class StageMeta(BaseModel):
    """Workflow stage metadata loaded from YAML rules."""

    model_config = ConfigDict(frozen=True)

    name: str
    type: str = "waiting"
    description: str = ""


class ThemePalettes(BaseModel):
    """Semantic theme palettes and priority rank order."""

    model_config = ConfigDict(frozen=True)

    light: dict[str, str]
    dark: dict[str, str]
    priority_order: list[str] = Field(default_factory=list)


class SyncStatus(BaseModel):
    """Layer 1 collector sync summary."""

    model_config = ConfigDict(frozen=True)

    status: str
    last_sync: str


class FilterOptions(BaseModel):
    """Global sidebar filter options and dataset date bounds."""

    model_config = ConfigDict(frozen=True)

    teams: list[str] = Field(default_factory=list)
    contexts: list[str] = Field(default_factory=list)
    milestones: list[str] = Field(default_factory=list)
    min_date: str | None = None
    max_date: str | None = None


class DashboardPayload(BaseModel):
    """Complete dataset and metadata served to the React dashboard."""

    model_config = ConfigDict(frozen=True)

    issues: list[IssueItem] = Field(default_factory=list)
    filter_options: FilterOptions
    label_styles: dict[str, LabelStyle] = Field(default_factory=dict)
    stages: list[StageMeta] = Field(default_factory=list)
    palettes: ThemePalettes
    sync_status: SyncStatus
    version: str = "0.1.0"
    generated_at: str


class AdminLoginRequest(BaseModel):
    """Admin authentication payload."""

    password: str


class AdminStatusResponse(BaseModel):
    """Current admin session authentication state."""

    model_config = ConfigDict(frozen=True)

    authenticated: bool


class AdminJobResponse(BaseModel):
    """Result of an admin pipeline command execution."""

    model_config = ConfigDict(frozen=True)

    step: str
    returncode: int
    stdout: str
    stderr: str
    success: bool


class HealthResponse(BaseModel):
    """Service liveness response."""

    model_config = ConfigDict(frozen=True)

    status: str = "ok"
