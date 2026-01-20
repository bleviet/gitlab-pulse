"""Modular YAML rule loader for Layer 2 validation.

Dynamically discovers and loads rule files from app/config/rules/*.yaml.
"""

import logging
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class LabelMappings(BaseModel):
    """Label mapping configuration."""

    type: dict[str, str] = Field(default_factory=dict)
    severity: dict[str, str] = Field(default_factory=dict)
    priority: dict[str, str] = Field(default_factory=dict)


class TitlePatterns(BaseModel):
    """Title pattern configuration for inferring type from issue title.

    Maps type names to lists of keywords (case-insensitive matching).
    Example: {"Bug": ["bug", "fix", "error"], "Feature": ["feature", "add"]}
    """

    type: dict[str, list[str]] = Field(default_factory=dict)  # type_name -> keywords


class ContextPattern(BaseModel):
    """Single context pattern definition."""

    prefix: str  # e.g., "rnd::" or "cust::"
    alias: str   # e.g., "R&D" or "Customer"


class ContextConfig(BaseModel):
    """Context slicing configuration for Data Explosion.

    Defines how to extract logical contexts from labels.
    """

    method: str = "label_prefix"  # Currently only supports "label_prefix"
    patterns: list[ContextPattern] = Field(default_factory=list)
    require_assignment: bool = False  # If true, missing context is a validation failure


class StageConfig(BaseModel):
    """Configuration for a single workflow stage."""

    name: str
    labels: list[str] = Field(default_factory=list)
    type: str = "waiting"  # "active", "waiting", "completed"
    description: str = Field(default="")


class WorkflowConfig(BaseModel):
    """Workflow process configuration."""

    stages: list[StageConfig] = Field(default_factory=list)


class ValidationConfig(BaseModel):
    """Validation rules configuration."""

    required_labels: dict[str, list[str]] = Field(default_factory=dict)
    required_fields: dict[str, list[str]] = Field(default_factory=dict)
    stale_threshold_days: int = 30
    max_cycle_time_days: int = 90


class CapacityConfig(BaseModel):
    """Configuration for Capacity view privacy and thresholds."""

    max_wip_per_person: int = 5
    max_contexts_per_person: int = 2
    anonymize_users: bool = False
    hidden_users: list[str] = Field(default_factory=list)


class DomainRule(BaseModel):
    """Schema for a domain rule configuration file."""

    project_ids: list[int] = Field(default_factory=list)
    team: str = "default"
    label_mappings: LabelMappings = Field(default_factory=LabelMappings)
    title_patterns: TitlePatterns = Field(default_factory=TitlePatterns)
    contexts: ContextConfig = Field(default_factory=ContextConfig)
    workflow: WorkflowConfig = Field(default_factory=WorkflowConfig)
    validation: ValidationConfig = Field(default_factory=ValidationConfig)
    capacity: CapacityConfig = Field(default_factory=CapacityConfig)
    colors: dict[str, str] = Field(default_factory=dict)



class ConfigurationConflictError(Exception):
    """Raised when multiple rule files claim the same project_id."""

    pass


class RuleLoader:
    """Loads and manages modular YAML rule configurations.

    Scans app/config/rules/*.yaml for rule files and validates them.
    """

    def __init__(self, rules_path: Path = Path("app/config/rules")) -> None:
        """Initialize the rule loader.

        Args:
            rules_path: Path to the rules directory
        """
        self.rules_path = rules_path
        self._rules: Optional[dict[int, DomainRule]] = None

    @property
    def rules(self) -> dict[int, DomainRule]:
        """Get rules indexed by project_id, loading if needed."""
        if self._rules is None:
            self._rules = self._load_all()
        return self._rules

    def get_rule(self, project_id: int) -> Optional[DomainRule]:
        """Get the rule configuration for a specific project.

        Args:
            project_id: GitLab project ID

        Returns:
            DomainRule for the project, or None if not configured
        """
        return self.rules.get(project_id)

    def get_default_rule(self) -> DomainRule:
        """Get a default rule configuration."""
        return DomainRule()

    def _load_all(self) -> dict[int, DomainRule]:
        """Load all rules from the rules directory.

        Returns:
            Dict mapping project_id to DomainRule

        Raises:
            ConfigurationConflictError: If multiple files claim the same project_id
        """
        rules: dict[int, DomainRule] = {}
        seen_projects: dict[int, str] = {}

        if not self.rules_path.exists():
            logger.warning(f"Rules path does not exist: {self.rules_path}")
            return rules

        for yaml_file in self.rules_path.glob("*.yaml"):
            try:
                rule = self._load_file(yaml_file)

                for project_id in rule.project_ids:
                    if project_id in seen_projects:
                        raise ConfigurationConflictError(
                            f"Project {project_id} is claimed by both "
                            f"'{seen_projects[project_id]}' and '{yaml_file.name}'"
                        )
                    seen_projects[project_id] = yaml_file.name
                    rules[project_id] = rule

            except ConfigurationConflictError:
                raise
            except Exception as e:
                logger.error(f"Failed to load rule file {yaml_file}: {e}")

        logger.info(f"Loaded {len(rules)} project rules from {len(seen_projects)} files")
        return rules

    def _load_file(self, filepath: Path) -> DomainRule:
        """Load and validate a single rule file."""
        with filepath.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data:
            return DomainRule()

        return DomainRule.model_validate(data)

    def reload(self) -> None:
        """Force reload of all rule files."""
        self._rules = None
        _ = self.rules  # Trigger load
