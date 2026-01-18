"""Synthetic Data Generator (Seeder) for Testing.

Generates realistic issue data directly to data/processed/
to test Layer 2 and Layer 3 without GitLab API access.
"""

import argparse
import logging
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from faker import Faker

logger = logging.getLogger(__name__)
fake = Faker()

# Label pools
TYPE_LABELS = ["type::bug", "type::feature", "type::task"]
SEVERITY_LABELS = ["severity::critical", "severity::high", "severity::medium", "severity::low"]
PRIORITY_LABELS = ["priority::1", "priority::2", "priority::3"]
CONTEXT_LABELS = ["rnd::Alpha", "rnd::Beta", "rnd::Gamma", "cust::BMW", "cust::Audi"]
WORKFLOW_LABELS = [
    "workflow::architecture",
    "workflow::implementation",
    "workflow::review",
    "workflow::test",
    "workflow::done",
]
WORK_ITEM_TYPES = ["ISSUE", "TASK"]


def generate_issues(
    count: int = 1000,
    project_ids: Optional[list[int]] = None,
    years: int = 2,
    inject_errors: bool = False,
    seed: Optional[int] = None,
) -> pd.DataFrame:
    """Generate synthetic issue data.

    Args:
        count: Number of issues to generate
        project_ids: List of project IDs (default: [101, 102, 103])
        years: Years of history to simulate
        inject_errors: Whether to inject quality errors
        seed: Random seed for reproducibility

    Returns:
        DataFrame with RawIssue schema
    """
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)
        Faker.seed(seed)

    if project_ids is None:
        project_ids = [101, 102, 103]

    now = datetime.now()
    start_date = now - timedelta(days=years * 365)

    issues: list[dict] = []

    for i in range(count):
        issue_id = 10000 + i
        project_id = random.choice(project_ids)

        # Temporal distribution (realistic aging)
        created_at = _random_date(start_date, now)

        # State distribution: ~60% closed, ~40% open
        is_closed = random.random() < 0.6

        if is_closed:
            # Exponential distribution for time-to-close (many quick, few long)
            days_to_close = int(np.random.exponential(14))  # Mean 14 days
            closed_at = min(created_at + timedelta(days=days_to_close), now)
            state = "closed"
        else:
            closed_at = None
            state = "opened"

        # Updated at: between created and now
        max_update = closed_at or now
        updated_at = _random_date(created_at, max_update)

        # Staleness injection: 10-15% of open issues are stale
        if state == "opened" and random.random() < 0.12:
            updated_at = now - timedelta(days=random.randint(35, 90))

        # Labels
        labels = _generate_labels(inject_errors, state)

        # Work item type
        work_item_type = random.choices(WORK_ITEM_TYPES, weights=[0.8, 0.2])[0]

        # Hierarchy (only for tasks)
        parent_id: Optional[int] = None
        if work_item_type == "TASK":
            # 90% of tasks have a parent
            if random.random() < 0.9:
                # Sometimes reference existing issue, sometimes orphan
                if inject_errors and random.random() < 0.02:
                    parent_id = 99999  # Zombie: non-existent parent
                elif i > 0:
                    parent_id = 10000 + random.randint(0, max(0, i - 1))

        issue = {
            "id": issue_id,
            "iid": i + 1,
            "project_id": project_id,
            "title": _generate_title(labels),
            "state": state,
            "created_at": created_at,
            "updated_at": updated_at,
            "closed_at": closed_at,
            "labels": labels,
            "work_item_type": work_item_type,
            "parent_id": parent_id,
            "child_ids": [],
            "web_url": f"https://gitlab.example.com/project/-/issues/{i + 1}",
            "assignee": fake.user_name() if random.random() < 0.8 else None,
            "milestone": f"v1.{random.randint(0, 5)}" if random.random() < 0.6 else None,
        }
        issues.append(issue)

    return pd.DataFrame(issues)


def _random_date(start: datetime, end: datetime) -> datetime:
    """Generate a random datetime between start and end."""
    delta = end - start
    random_seconds = random.randint(0, int(delta.total_seconds()))
    return start + timedelta(seconds=random_seconds)


def _generate_labels(inject_errors: bool = False, state: str = "opened") -> list[str]:
    """Generate a realistic label set."""
    labels: list[str] = []

    # Missing labels error (5%)
    if inject_errors and random.random() < 0.05:
        return []  # No labels at all

    # Conflicting labels error (1%)
    if inject_errors and random.random() < 0.01:
        return ["type::bug", "type::feature"]  # Conflict!

    # Normal label generation
    # Type label (95% have one)
    if random.random() < 0.95:
        labels.append(random.choice(TYPE_LABELS))

    # Severity label for bugs (85% have one)
    if "type::bug" in labels and random.random() < 0.85:
        labels.append(random.choice(SEVERITY_LABELS))

    # Priority label (70% have one)
    if random.random() < 0.7:
        labels.append(random.choice(PRIORITY_LABELS))

    # Context labels (80% have at least one)
    if random.random() < 0.8:
        if random.random() < 0.3:
            num_contexts = random.randint(2, 3)
            contexts = random.sample(CONTEXT_LABELS, min(num_contexts, len(CONTEXT_LABELS)))
            labels.extend(contexts)
        else:
            labels.append(random.choice(CONTEXT_LABELS))

    # Workflow labels (Assigned to almost all non-error issues)
    if state == "closed":
        # Closed issues are mostly Done, but sometimes just "closed" at another stage
        if random.random() < 0.9:
            labels.append("workflow::done")
        else:
            # 10% closed as "won't fix" or similar (stuck in review/design)
            labels.append(random.choice(WORKFLOW_LABELS[:-1]))
    else:
        # Open issues are in active/waiting stages (not Done)
        # Check if WORKFLOW_LABELS[:-1] is empty to avoid error
        active_stages = WORKFLOW_LABELS[:-1]
        if active_stages:
            labels.append(random.choice(active_stages))

    return labels


def _generate_title(labels: list[str]) -> str:
    """Generate a realistic issue title based on type."""
    if "type::bug" in labels:
        templates = [
            f"Fix {fake.word()} error in {fake.word()} module",
            f"Bug: {fake.sentence(nb_words=4)}",
            f"Crash when {fake.word(part_of_speech='verb')}ing {fake.word()}",
            f"Error handling for {fake.word()} fails",
        ]
    elif "type::feature" in labels:
        templates = [
            f"Add {fake.word()} feature to {fake.word()}",
            f"Implement {fake.word()} functionality",
            f"Feature: {fake.sentence(nb_words=4)}",
            f"Enable {fake.word()} support",
        ]
    else:
        templates = [
            f"Update {fake.word()} documentation",
            f"Refactor {fake.word()} component",
            f"Task: {fake.sentence(nb_words=4)}",
            f"Clean up {fake.word()} code",
        ]

    return random.choice(templates)


def seed_data(
    count: int = 1000,
    project_ids: Optional[list[int]] = None,
    inject_errors: bool = False,
    output_path: Path = Path("data/processed"),
    seed: Optional[int] = None,
) -> None:
    """Generate and save synthetic data to Parquet.

    Args:
        count: Number of issues to generate
        project_ids: List of project IDs
        inject_errors: Whether to inject quality errors
        output_path: Output directory for Parquet files
        seed: Random seed
    """
    if project_ids is None:
        project_ids = [101, 102, 103]

    output_path.mkdir(parents=True, exist_ok=True)

    logger.info(f"Generating {count} synthetic issues for projects {project_ids}")

    df = generate_issues(
        count=count,
        project_ids=project_ids,
        inject_errors=inject_errors,
        seed=seed,
    )

    # Save per-project files (like Layer 1 output)
    for project_id in project_ids:
        project_df = df[df["project_id"] == project_id]
        if project_df.empty:
            continue

        filepath = output_path / f"issues_{project_id}.parquet"
        project_df.to_parquet(filepath, engine="pyarrow", compression="snappy")
        logger.info(f"Wrote {len(project_df)} issues to {filepath}")

    logger.info(f"Seeding complete: {count} issues across {len(project_ids)} projects")


def main() -> None:
    """CLI entry point for the seeder."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    parser = argparse.ArgumentParser(description="GitLabInsight Synthetic Data Seeder")
    parser.add_argument("--count", type=int, default=1000, help="Number of issues to generate")
    parser.add_argument("--projects", type=str, default="101,102,103", help="Comma-separated project IDs")
    parser.add_argument("--inject-errors", action="store_true", help="Inject quality errors")
    parser.add_argument("--output", type=str, default="data/processed", help="Output directory")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    args = parser.parse_args()

    project_ids = [int(p.strip()) for p in args.projects.split(",")]

    seed_data(
        count=args.count,
        project_ids=project_ids,
        inject_errors=args.inject_errors,
        output_path=Path(args.output),
        seed=args.seed,
    )

    print(f"\n✅ Generated {args.count} synthetic issues")
    print(f"   Projects: {project_ids}")
    print(f"   Errors injected: {args.inject_errors}")
    print(f"   Output: {args.output}/")


if __name__ == "__main__":
    main()
