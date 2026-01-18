"""Layer 2 Processor Entry Point.

Loads processed data, enriches with metrics, validates, and outputs to analytics.
"""

import logging
from pathlib import Path

import pandas as pd

from app.processor.enricher import apply_label_mappings, enrich_metrics, explode_contexts
from app.processor.rule_loader import RuleLoader
from app.processor.validator import validate_issues

logger = logging.getLogger(__name__)


class Processor:
    """Layer 2 processor for domain logic and validation.

    Pipeline: Load L1 → Enrich → Validate → Write L2 (analytics + quality)
    """

    def __init__(
        self,
        data_path: Path = Path("data"),
        rules_path: Path = Path("app/config/rules"),
    ) -> None:
        """Initialize the processor.

        Args:
            data_path: Base path for data storage
            rules_path: Path to rules configuration
        """
        self.processed_path = data_path / "processed"
        self.analytics_path = data_path / "analytics"
        self.analytics_path.mkdir(parents=True, exist_ok=True)

        self.rule_loader = RuleLoader(rules_path)

    def process_all(self) -> dict[str, int]:
        """Process all projects from Layer 1 output.

        Returns:
            Dict with counts: {"valid": n, "quality": n}
        """
        all_valid: list[pd.DataFrame] = []
        all_quality: list[pd.DataFrame] = []

        # Find all processed parquet files
        parquet_files = list(self.processed_path.glob("issues_*.parquet"))

        if not parquet_files:
            logger.warning("No processed data found in Layer 1 output")
            return {"valid": 0, "quality": 0}

        for filepath in parquet_files:
            project_id = self._extract_project_id(filepath)
            if project_id is None:
                continue

            try:
                valid_df, quality_df = self.process_project(project_id)
                if not valid_df.empty:
                    all_valid.append(valid_df)
                if not quality_df.empty:
                    all_quality.append(quality_df)
            except Exception as e:
                logger.error(f"Failed to process project {project_id}: {e}")

        # Combine and write output
        valid_count = 0
        quality_count = 0

        if all_valid:
            combined_valid = pd.concat(all_valid, ignore_index=True)
            self._write_parquet(combined_valid, self.analytics_path / "issues_valid.parquet")
            valid_count = len(combined_valid)

        if all_quality:
            combined_quality = pd.concat(all_quality, ignore_index=True)
            self._write_parquet(combined_quality, self.analytics_path / "data_quality.parquet")
            quality_count = len(combined_quality)

        logger.info(f"Processed: {valid_count} valid, {quality_count} quality issues")
        return {"valid": valid_count, "quality": quality_count}

    def process_project(self, project_id: int) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Process a single project.

        Args:
            project_id: GitLab project ID

        Returns:
            Tuple of (valid_df, quality_df)
        """
        filepath = self.processed_path / f"issues_{project_id}.parquet"
        if not filepath.exists():
            logger.warning(f"No data file for project {project_id}")
            return pd.DataFrame(), pd.DataFrame()

        # Load Layer 1 data
        df = pd.read_parquet(filepath)
        logger.info(f"Loaded {len(df)} issues for project {project_id}")

        # Get rule for this project
        rule = self.rule_loader.get_rule(project_id)
        if rule is None:
            rule = self.rule_loader.get_default_rule()
            logger.debug(f"Using default rule for project {project_id}")

        # Enrich with metrics
        df = enrich_metrics(df, rule)
        df = apply_label_mappings(df, rule)

        # Context explosion (Data Explosion pattern)
        df, orphan_df = explode_contexts(df, rule)

        # Validate
        result = validate_issues(df, rule)

        # Add orphan issues as MISSING_CONTEXT quality failures
        if not orphan_df.empty:
            orphan_df = orphan_df.copy()
            orphan_df["error_code"] = "MISSING_CONTEXT"
            orphan_df["error_message"] = "Issue not assigned to any context/project"
            result.quality_df = pd.concat([result.quality_df, orphan_df], ignore_index=True)

        return result.valid_df, result.quality_df

    def _extract_project_id(self, filepath: Path) -> int | None:
        """Extract project ID from filename (issues_{project_id}.parquet)."""
        try:
            name = filepath.stem  # issues_123
            return int(name.split("_")[1])
        except (IndexError, ValueError):
            return None

    def _write_parquet(self, df: pd.DataFrame, filepath: Path) -> None:
        """Write DataFrame to Parquet atomically."""
        tmp_filepath = filepath.with_suffix(".tmp")
        df.to_parquet(tmp_filepath, engine="pyarrow", compression="snappy")
        tmp_filepath.replace(filepath)
        logger.info(f"Wrote {len(df)} rows to {filepath}")


def main() -> None:
    """CLI entry point for the processor."""
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    parser = argparse.ArgumentParser(description="GitLabInsight Layer 2 Processor")
    parser.add_argument("--data-path", type=str, default="data", help="Data directory path")
    parser.add_argument("--rules-path", type=str, default="app/config/rules", help="Rules directory")
    args = parser.parse_args()

    processor = Processor(
        data_path=Path(args.data_path),
        rules_path=Path(args.rules_path),
    )

    results = processor.process_all()
    print(f"\nProcessing complete: {results['valid']} valid, {results['quality']} quality issues")


if __name__ == "__main__":
    main()
