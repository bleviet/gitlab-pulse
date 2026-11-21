"""Pydantic v2 response and request schemas for the dashboard API."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.processor.preview import ImpactSummary


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
    impact: str | None = None
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


class ClassificationValueModel(BaseModel):
    """One classification value with its label and title match patterns."""

    name: str
    labels: list[str] = Field(default_factory=list)
    title: list[str] = Field(default_factory=list)


class ClassificationCategoryModel(BaseModel):
    """A classification category holding its values in match order."""

    name: str
    values: list[ClassificationValueModel] = Field(default_factory=list)


class ContextRuleModel(BaseModel):
    """A context rule matching issues by label or title patterns."""

    name: str
    labels: list[str] = Field(default_factory=list)
    title: list[str] = Field(default_factory=list)


class ContextsModel(BaseModel):
    """Context slicing configuration."""

    rules: list[ContextRuleModel] = Field(default_factory=list)
    require_assignment: bool = False


class WorkflowStageModel(BaseModel):
    """A workflow stage with its label patterns."""

    name: str
    labels: list[str] = Field(default_factory=list)
    type: str = "waiting"
    description: str = ""


class WorkflowModel(BaseModel):
    """Workflow stages in board order."""

    stages: list[WorkflowStageModel] = Field(default_factory=list)


class ValidationModel(BaseModel):
    """Data quality thresholds and required labels or fields."""

    required_labels: dict[str, list[str]] = Field(default_factory=dict)
    required_fields: dict[str, list[str]] = Field(default_factory=dict)
    stale_threshold_days: int = 30
    max_cycle_time_days: int = 90


class RuleSetBody(BaseModel):
    """Editable content of one rule set; classification order is significant."""

    project_ids: list[int] = Field(default_factory=list)
    team: str = "default"
    classification: list[ClassificationCategoryModel] = Field(default_factory=list)
    contexts: ContextsModel
    workflow: WorkflowModel
    validation: ValidationModel
    colors: dict[str, Any] = Field(default_factory=dict)


class RuleSetItem(BaseModel):
    """A stored rule set with its name and content revision."""

    model_config = ConfigDict(frozen=True)

    name: str
    revision: str
    rule: RuleSetBody


class PaletteDefaults(BaseModel):
    """Built-in semantic colors used when a rule set sets no override."""

    model_config = ConfigDict(frozen=True)

    light: dict[str, str]
    dark: dict[str, str]


class RuleSetsResponse(BaseModel):
    """All rule sets, files that failed to load, and where they came from."""

    model_config = ConfigDict(frozen=True)

    rule_sets: list[RuleSetItem]
    load_errors: dict[str, str] = Field(default_factory=dict)
    source: Literal["template", "user"]
    default_name: str | None = None
    palette_defaults: PaletteDefaults


class RuleProblemModel(BaseModel):
    """A fixable problem in a submitted rule set."""

    model_config = ConfigDict(frozen=True)

    path: str
    message: str


class RuleSaveRequest(BaseModel):
    """Rule set edit based on a previously loaded revision."""

    revision: str
    rule: RuleSetBody


class RuleSaveResponse(BaseModel):
    """Saved rule set and the result of the processor re-run."""

    model_config = ConfigDict(frozen=True)

    rule_set: RuleSetItem
    job: AdminJobResponse


class RulePreviewRequest(BaseModel):
    """Draft rule set to preview without saving."""

    rule: RuleSetBody


class RulePreviewResponse(BaseModel):
    """Problems with the draft, or its impact when the draft is valid."""

    model_config = ConfigDict(frozen=True)

    problems: list[RuleProblemModel] = Field(default_factory=list)
    impact: ImpactSummary | None = None


class RuleCreateRequest(BaseModel):
    """New rule set; its file name is derived from the team name."""

    rule: RuleSetBody


class RuleDeleteResponse(BaseModel):
    """Result of the processor re-run after deleting a rule set."""

    model_config = ConfigDict(frozen=True)

    job: AdminJobResponse


class RuleVersionModel(BaseModel):
    """An earlier version of a rule set."""

    model_config = ConfigDict(frozen=True)

    id: str
    kind: Literal["history", "template"]
    saved_at: str | None = None


class RuleVersionsResponse(BaseModel):
    """Earlier versions of a rule set, newest first."""

    model_config = ConfigDict(frozen=True)

    versions: list[RuleVersionModel] = Field(default_factory=list)


class RuleVersionResponse(BaseModel):
    """Content of one earlier version of a rule set."""

    model_config = ConfigDict(frozen=True)

    rule: RuleSetBody


class RuleTextResponse(BaseModel):
    """A rule file's location and content as stored on disk."""

    model_config = ConfigDict(frozen=True)

    path: str
    text: str


class RuleTextSaveRequest(BaseModel):
    """Request body for saving raw YAML text for an existing rule set."""

    revision: str
    text: str
