"""Read, validate, and write rule files edited through the settings UI.

Layer 2 owns the rule file format. UI-saved rules live in ``data/rules/``;
``app/config/rules/`` is a read-only template used until the first save.
"""

import hashlib
import logging
import os
import re
import shutil
from collections.abc import Collection, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict

from app.processor.rule_loader import (
    DEFAULT_TEMPLATE_RULES_PATH,
    DEFAULT_USER_RULES_PATH,
    DomainRule,
    load_rule_file,
    resolve_rules_path,
)

logger = logging.getLogger(__name__)

HISTORY_DIR_NAME = ".history"
HISTORY_KEEP = 20
_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
_VERSION_ID_PATTERN = re.compile(r"\d{8}T\d{12}Z")
TEMPLATE_VERSION_ID = "template"
_MAX_SLUG_LENGTH = 60
_STAMP_FORMAT = "%Y%m%dT%H%M%S%fZ"
_INVALID_NAME_MESSAGE = (
    "Rule set names may only use lowercase letters, digits, '-' and '_'."
)
_STAGE_TYPES = ("active", "waiting", "completed")
_PATTERN_PREFIXES = ("regex:", "contains:", "exact:")
_FILE_HEADER = (
    "# Managed by the GitLab Pulse settings UI. "
    "Comments in this file are not preserved.\n"
)


class RuleProblem(BaseModel):
    """A single problem found in a rule set, addressed by its field path."""

    model_config = ConfigDict(frozen=True)

    path: str
    message: str


class StoredRuleSet(BaseModel):
    """A rule file on disk together with its content revision."""

    model_config = ConfigDict(frozen=True)

    name: str
    revision: str
    rule: DomainRule


class RuleVersion(BaseModel):
    """An earlier version of a rule set that can be loaded back into the editor."""

    model_config = ConfigDict(frozen=True)

    id: str
    kind: Literal["history", "template"]
    saved_at: datetime | None


class RuleSetNotFoundError(Exception):
    """Raised when the named rule set does not exist."""


class RuleSetExistsError(Exception):
    """Raised when creating a rule set whose name is already taken."""


class RuleVersionNotFoundError(Exception):
    """Raised when the requested version of a rule set does not exist."""


class RevisionConflictError(Exception):
    """Raised when the rule file changed since the caller read it."""


class InvalidRuleSetNameError(Exception):
    """Raised when a rule set name is not a safe file stem."""


def unique_name(team: str, existing: Collection[str]) -> str:
    """Derive an unused rule set name from a team name.

    Args:
        team: Team name typed by the user
        existing: Rule set names already in use

    Returns:
        A slug of the team name, suffixed ``-2``, ``-3``, ... when taken
    """
    slug = re.sub(r"[^a-z0-9]+", "-", team.lower()).strip("-")
    slug = slug[:_MAX_SLUG_LENGTH].strip("-") or "rule-set"
    if slug not in existing:
        return slug
    suffix = 2
    while f"{slug}-{suffix}" in existing:
        suffix += 1
    return f"{slug}-{suffix}"


def effective_default_name(rule_sets: Mapping[str, DomainRule]) -> str | None:
    """Name of the rule set the processor uses for projects without their own.

    Among rule sets with an empty ``project_ids`` list, the one whose file name
    sorts first wins, as in ``RuleLoader``.

    Args:
        rule_sets: Rule sets by name

    Returns:
        The name of the effective default, or None when there is none
    """
    candidates = [name for name, rule in rule_sets.items() if not rule.project_ids]
    return min(candidates, key=lambda name: f"{name}.yaml", default=None)


def dump_rule(rule: DomainRule) -> str:
    """Serialize a rule to YAML text, omitting deprecated keys.

    Key order is preserved because the order of classification values is
    behaviour (first match wins; priority order is the rank).

    Args:
        rule: The rule to serialize

    Returns:
        File content starting with a one-line header comment
    """
    data = rule.model_dump(
        exclude={
            "label_mappings": True,
            "title_patterns": True,
            "contexts": {"method": True, "patterns": True},
        }
    )
    body: str = yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
    return _FILE_HEADER + body


def _revision(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _write_atomic(target: Path, content: bytes) -> None:
    tmp_path = target.with_name(f"{target.name}.tmp")
    tmp_path.write_bytes(content)
    os.replace(tmp_path, target)


def _check_patterns(
    patterns: list[str], base_path: str, problems: list[RuleProblem]
) -> None:
    for index, pattern in enumerate(patterns):
        path = f"{base_path}.{index}"
        value = pattern
        is_regex = False
        for prefix in _PATTERN_PREFIXES:
            if pattern.startswith(prefix):
                value = pattern[len(prefix) :]
                is_regex = prefix == "regex:"
                break
        if not value.strip():
            problems.append(
                RuleProblem(path=path, message="This match text is empty. Enter text or remove it.")
            )
        elif is_regex:
            try:
                re.compile(value)
            except re.error as exc:
                problems.append(
                    RuleProblem(
                        path=path,
                        message=f"This advanced pattern is not valid: {exc}.",
                    )
                )


def validate_rule_set(
    rule: DomainRule, others: Mapping[str, DomainRule]
) -> list[RuleProblem]:
    """Check a rule set for mistakes a user can fix.

    Args:
        rule: The rule set being validated
        others: The other rule sets by name, excluding the one being validated

    Returns:
        A list of problems; empty when the rule set is valid
    """
    problems: list[RuleProblem] = []

    if not rule.team.strip():
        problems.append(
            RuleProblem(path="team", message="Give this rule set a team name.")
        )

    for category, values in rule.classification.items():
        for index, (value_name, match) in enumerate(values.items()):
            base = f"classification.{category}.{index}"
            if not value_name.strip():
                problems.append(
                    RuleProblem(
                        path=f"{base}.name",
                        message="Every value needs a name.",
                    )
                )
            _check_patterns(match.labels, f"{base}.labels", problems)
            _check_patterns(match.title, f"{base}.title", problems)

    seen_stages: set[str] = set()
    for index, stage in enumerate(rule.workflow.stages):
        base = f"workflow.stages.{index}"
        stage_name = stage.name.strip()
        if not stage_name:
            problems.append(
                RuleProblem(path=f"{base}.name", message="Every stage needs a name.")
            )
        elif stage_name in seen_stages:
            problems.append(
                RuleProblem(
                    path=f"{base}.name",
                    message=f"There is more than one stage named '{stage_name}'.",
                )
            )
        seen_stages.add(stage_name)
        if stage.type not in _STAGE_TYPES:
            problems.append(
                RuleProblem(
                    path=f"{base}.type",
                    message="Choose one of: active, waiting, completed.",
                )
            )
        _check_patterns(stage.labels, f"{base}.labels", problems)

    seen_contexts: set[str] = set()
    for index, context in enumerate(rule.contexts.rules):
        base = f"contexts.rules.{index}"
        context_name = context.name.strip()
        if not context_name:
            problems.append(
                RuleProblem(path=f"{base}.name", message="Every context needs a name.")
            )
        elif context_name in seen_contexts:
            problems.append(
                RuleProblem(
                    path=f"{base}.name",
                    message=f"There is more than one context named '{context_name}'.",
                )
            )
        seen_contexts.add(context_name)
        _check_patterns(context.labels, f"{base}.labels", problems)
        _check_patterns(context.title, f"{base}.title", problems)

    for issue_type, patterns in rule.validation.required_labels.items():
        _check_patterns(patterns, f"validation.required_labels.{issue_type}", problems)

    if rule.validation.stale_threshold_days < 1:
        problems.append(
            RuleProblem(
                path="validation.stale_threshold_days",
                message="Enter at least 1 day.",
            )
        )
    if rule.validation.max_cycle_time_days < 1:
        problems.append(
            RuleProblem(
                path="validation.max_cycle_time_days",
                message="Enter at least 1 day.",
            )
        )

    for other_name, other in others.items():
        shared = sorted(set(rule.project_ids) & set(other.project_ids))
        if shared:
            ids = ", ".join(str(project_id) for project_id in shared)
            problems.append(
                RuleProblem(
                    path="project_ids",
                    message=(
                        f"Project {ids} is already used by the rule set "
                        f"'{other_name}'."
                    ),
                )
            )
        if not rule.project_ids and not other.project_ids:
            problems.append(
                RuleProblem(
                    path="project_ids",
                    message=(
                        f"The rule set '{other_name}' already applies to all other "
                        "projects. Only one rule set can do that."
                    ),
                )
            )

    return problems


class RuleStore:
    """Reads and writes rule sets, copying the template on the first save."""

    def __init__(
        self,
        user_path: Path = DEFAULT_USER_RULES_PATH,
        template_path: Path = DEFAULT_TEMPLATE_RULES_PATH,
    ) -> None:
        """Initialize the store.

        Args:
            user_path: Directory for rules saved from the UI
            template_path: Read-only template rules directory
        """
        self.user_path = user_path
        self.template_path = template_path

    @property
    def active_path(self) -> Path:
        """Directory currently providing the rules."""
        return resolve_rules_path(self.user_path, self.template_path)

    @property
    def source(self) -> Literal["user", "template"]:
        """Whether the active rules come from the user directory or the template."""
        return "user" if self.active_path == self.user_path else "template"

    def list_rule_sets(self) -> tuple[list[StoredRuleSet], dict[str, str]]:
        """Read every rule file in the active directory.

        Returns:
            The valid rule sets, and a mapping of filename to error message for
            files that could not be loaded.
        """
        rule_sets: list[StoredRuleSet] = []
        errors: dict[str, str] = {}
        active = self.active_path
        if not active.is_dir():
            return rule_sets, errors
        for yaml_file in sorted(active.glob("*.yaml")):
            try:
                content = yaml_file.read_bytes()
                rule = load_rule_file(yaml_file)
            except Exception as exc:
                logger.error(f"Failed to load rule file {yaml_file}: {exc}")
                errors[yaml_file.name] = str(exc)
                continue
            rule_sets.append(
                StoredRuleSet(
                    name=yaml_file.stem, revision=_revision(content), rule=rule
                )
            )
        return rule_sets, errors

    def check_exists(self, name: str) -> None:
        """Check that a rule set name is safe and refers to an existing file.

        Args:
            name: Rule set name (file stem)

        Raises:
            InvalidRuleSetNameError: If the name is not a safe file stem
            RuleSetNotFoundError: If no rule file has this name
        """
        if not _NAME_PATTERN.fullmatch(name):
            raise InvalidRuleSetNameError(_INVALID_NAME_MESSAGE)
        if not (self.active_path / f"{name}.yaml").is_file():
            raise RuleSetNotFoundError(f"Rule set '{name}' does not exist.")

    def write(
        self, name: str, rule: DomainRule, expected_revision: str
    ) -> StoredRuleSet:
        """Replace an existing rule set, keeping a history copy of the old file.

        Args:
            name: Rule set name (file stem)
            rule: The new rule content
            expected_revision: Revision the caller based its edit on

        Returns:
            The stored rule set with its new revision

        Raises:
            InvalidRuleSetNameError: If the name is not a safe file stem
            RuleSetNotFoundError: If no rule file has this name
            RevisionConflictError: If the file changed since it was read
        """
        self.check_exists(name)
        current = self.active_path / f"{name}.yaml"
        if _revision(current.read_bytes()) != expected_revision:
            raise RevisionConflictError(
                f"Rule set '{name}' changed since it was loaded."
            )

        self._seed_from_template()

        target = self.user_path / f"{name}.yaml"
        self._archive(target, name)

        content = dump_rule(rule).encode("utf-8")
        _write_atomic(target, content)
        return StoredRuleSet(name=name, revision=_revision(content), rule=rule)

    def create(self, name: str, rule: DomainRule) -> StoredRuleSet:
        """Create a new rule set.

        Args:
            name: Rule set name (file stem)
            rule: The rule content

        Returns:
            The stored rule set with its revision

        Raises:
            InvalidRuleSetNameError: If the name is not a safe file stem
            RuleSetExistsError: If a rule set with this name already exists
        """
        if not _NAME_PATTERN.fullmatch(name):
            raise InvalidRuleSetNameError(_INVALID_NAME_MESSAGE)
        if (self.active_path / f"{name}.yaml").exists():
            raise RuleSetExistsError(f"Rule set '{name}' already exists.")
        self._seed_from_template()
        content = dump_rule(rule).encode("utf-8")
        _write_atomic(self.user_path / f"{name}.yaml", content)
        return StoredRuleSet(name=name, revision=_revision(content), rule=rule)

    def delete(self, name: str, expected_revision: str) -> None:
        """Delete a rule set, keeping a history copy of the removed file.

        Args:
            name: Rule set name (file stem)
            expected_revision: Revision the caller based its decision on

        Raises:
            InvalidRuleSetNameError: If the name is not a safe file stem
            RuleSetNotFoundError: If no rule file has this name
            RevisionConflictError: If the file changed since it was read
        """
        self.check_exists(name)
        current = self.active_path / f"{name}.yaml"
        if _revision(current.read_bytes()) != expected_revision:
            raise RevisionConflictError(
                f"Rule set '{name}' changed since it was loaded."
            )
        self._seed_from_template()
        target = self.user_path / f"{name}.yaml"
        self._archive(target, name)
        target.unlink()

    def list_versions(self, name: str) -> list[RuleVersion]:
        """List earlier versions of a rule set, newest first, then the template.

        Args:
            name: Rule set name (file stem)

        Returns:
            History versions followed by the template version when one exists

        Raises:
            InvalidRuleSetNameError: If the name is not a safe file stem
            RuleSetNotFoundError: If no rule file has this name
        """
        self.check_exists(name)
        history_dir = self.user_path / HISTORY_DIR_NAME
        versions: list[RuleVersion] = []
        for path in sorted(history_dir.glob(self._history_glob(name)), reverse=True):
            version_id = path.stem[len(name) + 1 :]
            saved_at = datetime.strptime(version_id, _STAMP_FORMAT).replace(tzinfo=UTC)
            versions.append(
                RuleVersion(id=version_id, kind="history", saved_at=saved_at)
            )
        if (self.template_path / f"{name}.yaml").is_file():
            versions.append(
                RuleVersion(id=TEMPLATE_VERSION_ID, kind="template", saved_at=None)
            )
        return versions

    def read_version(self, name: str, version_id: str) -> DomainRule:
        """Load an earlier version of a rule set.

        Args:
            name: Rule set name (file stem)
            version_id: A history version id, or ``template``

        Returns:
            The rule content of that version

        Raises:
            InvalidRuleSetNameError: If the name is not a safe file stem
            RuleSetNotFoundError: If no rule file has this name
            RuleVersionNotFoundError: If the version id is malformed or missing
        """
        self.check_exists(name)
        if version_id == TEMPLATE_VERSION_ID:
            path = self.template_path / f"{name}.yaml"
        elif _VERSION_ID_PATTERN.fullmatch(version_id):
            path = self.user_path / HISTORY_DIR_NAME / f"{name}-{version_id}.yaml"
        else:
            raise RuleVersionNotFoundError("This version does not exist.")
        if not path.is_file():
            raise RuleVersionNotFoundError("This version does not exist.")
        return load_rule_file(path)

    def _seed_from_template(self) -> None:
        if self.source != "template":
            return
        self.user_path.mkdir(parents=True, exist_ok=True)
        for template_file in sorted(self.template_path.glob("*.yaml")):
            _write_atomic(
                self.user_path / template_file.name, template_file.read_bytes()
            )

    @staticmethod
    def _history_glob(name: str) -> str:
        return f"{name}-????????T????????????Z.yaml"

    def _archive(self, target: Path, name: str) -> None:
        history_dir = self.user_path / HISTORY_DIR_NAME
        history_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).strftime(_STAMP_FORMAT)
        shutil.copyfile(target, history_dir / f"{name}-{stamp}.yaml")
        history = sorted(history_dir.glob(self._history_glob(name)))
        for stale in history[:-HISTORY_KEEP]:
            stale.unlink()
