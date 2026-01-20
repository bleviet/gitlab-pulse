"""Unit tests for Layer 2 Validator."""

import pandas as pd
import pytest

from app.processor.enricher import apply_classification, enrich_metrics
from app.processor.rule_loader import DomainRule, LabelMappings, ValidationConfig
from app.processor.validator import ErrorCodes, validate_issues


@pytest.fixture
def sample_rule() -> DomainRule:
    """Create a sample domain rule for testing."""
    return DomainRule(
        project_ids=[101],
        team="test-team",
        label_mappings=LabelMappings(
            type={
                "type::bug": "Bug",
                "type::feature": "Feature",
                "type::task": "Task",
            },
            severity={
                "severity::high": "High",
                "severity::low": "Low",
            },
        ),
        validation=ValidationConfig(
            required_labels={"Bug": ["contains:severity::"]},
            stale_threshold_days=30,
        ),
    )


@pytest.fixture
def sample_issues_df() -> pd.DataFrame:
    """Create a sample DataFrame with test issues."""
    return pd.DataFrame([
        {
            "id": 1,
            "iid": 1,
            "project_id": 101,
            "title": "Perfect bug",
            "state": "opened",
            "created_at": pd.Timestamp("2024-01-01", tz="UTC"),
            "updated_at": pd.Timestamp("2024-01-15", tz="UTC"),
            "closed_at": None,
            "labels": ["type::bug", "severity::high"],
            "work_item_type": "ISSUE",
            "parent_id": None,
        },
        {
            "id": 2,
            "iid": 2,
            "project_id": 101,
            "title": "Bug missing severity",
            "state": "opened",
            "created_at": pd.Timestamp("2024-01-01", tz="UTC"),
            "updated_at": pd.Timestamp("2024-01-15", tz="UTC"),
            "closed_at": None,
            "labels": ["type::bug"],  # Missing severity
            "work_item_type": "ISSUE",
            "parent_id": None,
        },
        {
            "id": 3,
            "iid": 3,
            "project_id": 101,
            "title": "Feature (valid)",
            "state": "closed",
            "created_at": pd.Timestamp("2024-01-01", tz="UTC"),
            "updated_at": pd.Timestamp("2024-01-10", tz="UTC"),
            "closed_at": pd.Timestamp("2024-01-08", tz="UTC"),
            "labels": ["type::feature"],
            "work_item_type": "ISSUE",
            "parent_id": None,
        },
        {
            "id": 4,
            "iid": 4,
            "project_id": 101,
            "title": "Conflicting labels",
            "state": "opened",
            "created_at": pd.Timestamp("2024-01-01", tz="UTC"),
            "updated_at": pd.Timestamp("2024-01-15", tz="UTC"),
            "closed_at": None,
            "labels": ["type::bug", "type::feature"],  # Conflict!
            "work_item_type": "ISSUE",
            "parent_id": None,
        },
    ])


class TestEnricher:
    """Tests for the enricher module."""

    def test_enrich_metrics_adds_age_days(self, sample_issues_df: pd.DataFrame, sample_rule: DomainRule) -> None:
        """Test that age_days is calculated correctly."""
        result = enrich_metrics(sample_issues_df, sample_rule)
        assert "age_days" in result.columns
        assert result["age_days"].notna().all()

    def test_enrich_metrics_adds_cycle_time(self, sample_issues_df: pd.DataFrame, sample_rule: DomainRule) -> None:
        """Test that cycle_time is calculated for closed issues."""
        result = enrich_metrics(sample_issues_df, sample_rule)
        assert "cycle_time" in result.columns
        # Only closed issue (id=3) should have cycle_time
        closed_row = result[result["id"] == 3]
        assert closed_row["cycle_time"].notna().all()


    def test_apply_label_mappings(self, sample_issues_df: pd.DataFrame, sample_rule: DomainRule) -> None:
        """Test that classification rules are applied correctly."""
        result = apply_classification(sample_issues_df, sample_rule)
        assert "issue_type" in result.columns
        assert "team" in result.columns

        # Check specific mappings
        bug_row = result[result["id"] == 1]
        assert bug_row["issue_type"].iloc[0] == "Bug"


class TestValidator:
    """Tests for the validator module."""

    def test_validate_perfect_bug_passes(self, sample_issues_df: pd.DataFrame, sample_rule: DomainRule) -> None:
        """Test that a properly labeled bug passes validation."""
        enriched = enrich_metrics(sample_issues_df, sample_rule)
        enriched = apply_classification(enriched, sample_rule)

        result = validate_issues(enriched, sample_rule)

        # Issue 1 (perfect bug) should be valid
        assert 1 in result.valid_df["id"].values

    def test_validate_missing_severity_fails(self, sample_issues_df: pd.DataFrame, sample_rule: DomainRule) -> None:
        """Test that a bug without severity fails validation."""
        enriched = enrich_metrics(sample_issues_df, sample_rule)
        enriched = apply_classification(enriched, sample_rule)

        result = validate_issues(enriched, sample_rule)

        # Issue 2 (missing severity) should be in quality
        assert 2 in result.quality_df["id"].values
        error_row = result.quality_df[result.quality_df["id"] == 2]
        assert error_row["error_code"].iloc[0] == ErrorCodes.MISSING_LABEL

    def test_validate_conflicting_labels_fails(self, sample_issues_df: pd.DataFrame, sample_rule: DomainRule) -> None:
        """Test that conflicting type labels fail validation."""
        enriched = enrich_metrics(sample_issues_df, sample_rule)
        enriched = apply_classification(enriched, sample_rule)

        result = validate_issues(enriched, sample_rule)

        # Issue 4 (conflicting labels) should be in quality
        assert 4 in result.quality_df["id"].values
        # Check that CONFLICTING_LABELS error is present for this issue
        issue_4_errors = result.quality_df[result.quality_df["id"] == 4]["error_code"].tolist()
        assert ErrorCodes.CONFLICTING_LABELS in issue_4_errors

    def test_validate_feature_passes(self, sample_issues_df: pd.DataFrame, sample_rule: DomainRule) -> None:
        """Test that a feature (no severity required) passes validation."""
        enriched = enrich_metrics(sample_issues_df, sample_rule)
        enriched = apply_classification(enriched, sample_rule)

        result = validate_issues(enriched, sample_rule)

        # Issue 3 (feature) should be valid
        assert 3 in result.valid_df["id"].values
