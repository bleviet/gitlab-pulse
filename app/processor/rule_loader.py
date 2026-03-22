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


class ContextRule(BaseModel):
    """Context logic rule definition."""

    name: str
    labels: list[str] = Field(default_factory=list)
    title: list[str] = Field(default_factory=list)


class ContextPattern(BaseModel):
    """Single context pattern definition."""

    prefix: str  # e.g., "rnd::" or "cust::"
    alias: str   # e.g., "R&D" or "Customer"


class ContextConfig(BaseModel):
    """Context slicing configuration for Data Explosion.

    Defines how to extract logical contexts from labels/titles.
    """

    method: Optional[str] = None  # Deprecated
    patterns: list[ContextPattern] = Field(default_factory=list)  # Deprecated
    rules: list[ContextRule] = Field(default_factory=list)
    require_assignment: bool = False

    def model_post_init(self, __context: Any) -> None:
        """Migrate deprecated patterns to rules."""
        if self.patterns and not self.rules:
            self._migrate_patterns()

    def _migrate_patterns(self) -> None:
        """Convert legacy patterns to rules."""
        for pattern in self.patterns:
            # Legacy patterns were prefix-based
            self.rules.append(
                ContextRule(
                    name=pattern.alias,
                    labels=[f"contains:{pattern.prefix}"],
                )
            )


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


class ClassificationMatch(BaseModel):
    """Rules for matching a specific classification value."""

    labels: list[str] = Field(default_factory=list)
    title: list[str] = Field(default_factory=list)


class DomainRule(BaseModel):
    """Schema for a domain rule configuration file."""

    project_ids: list[int] = Field(default_factory=list)
    team: str = "default"
    
    # Legacy mappings (Deprecated)
    label_mappings: LabelMappings = Field(default_factory=LabelMappings)
    title_patterns: TitlePatterns = Field(default_factory=TitlePatterns)
    
    # New unified classification
    # Structure: Category -> Value -> Match Rules
    # e.g. {"type": {"Bug": ClassificationMatch(labels=["type::bug"], ...)}}
    classification: dict[str, dict[str, ClassificationMatch]] = Field(default_factory=dict)
    
    contexts: ContextConfig = Field(default_factory=ContextConfig)
    workflow: WorkflowConfig = Field(default_factory=WorkflowConfig)
    validation: ValidationConfig = Field(default_factory=ValidationConfig)
    colors: dict[str, Any] = Field(default_factory=dict)

    def model_post_init(self, __context: Any) -> None:
        """Migrate legacy mappings to classification."""
        if not self.classification and (self.label_mappings or self.title_patterns):
            self._migrate_mappings()
            
    def _migrate_mappings(self) -> None:
        """Convert legacy label relationships to classification rules."""
        # Helper to ensure category dict exists
        def get_match_rule(category: str, value: str) -> ClassificationMatch:
            if category not in self.classification:
                self.classification[category] = {}
            if value not in self.classification[category]:
                self.classification[category][value] = ClassificationMatch()
            return self.classification[category][value]

        # 1. Migrate Label Mappings
        # label_mappings.type: {"type::bug": "Bug"}
        for key, value in self.label_mappings.type.items():
            rule = get_match_rule("type", value)
            rule.labels.append(key) # Treat as exact/prefix based on utils logic? 
            # Note: utils.has_any_label checks exact match if no prefix.
            # Legacy simple strings were exact matches usually.
            
        for key, value in self.label_mappings.severity.items():
             get_match_rule("severity", value).labels.append(key)
             
        for key, value in self.label_mappings.priority.items():
             get_match_rule("priority", value).labels.append(key)
             
        # 2. Migrate Title Patterns
        # title_patterns.type: {"Bug": ["bug", "fix"]}
        for type_name, keywords in self.title_patterns.type.items():
            rule = get_match_rule("type", type_name)
            for kw in keywords:
                # Title patterns were substring matches
                rule.title.append(f"contains:{kw}")




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
