"""Synthetic Data Generator (Seeder) for Testing.

Generates realistic issue data directly to data/processed/
to test Layer 2 and Layer 3 without GitLab API access.
"""

import argparse
import logging
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Final, cast
from urllib.parse import urlencode

import numpy as np
import pandas as pd
from faker import Faker

logger = logging.getLogger(__name__)
fake = Faker()
DEFAULT_PROJECT_IDS: Final[list[int]] = [101, 102, 103]
DEFAULT_ASSIGNMENT_RATE: Final[float] = 0.95
DEFAULT_MAX_TEAM_MEMBERS: Final[int] = 12
DEFAULT_DASHBOARD_URL_BASE: Final[str] = "http://localhost:8501"

# Label pools
TYPE_LABELS = ["type::bug", "type::feature", "type::task"]
SEVERITY_LABELS = ["severity::critical", "severity::high", "severity::medium", "severity::low"]
PRIORITY_LABELS = ["priority::1", "priority::2", "priority::3"]
CONTEXT_LABELS = [
    "project::A", "project::B", "project::C",
    "p1-urgent", "critical-incident", # For "Urgent" context
    "security", "cve", # For "Security" context
]
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
    project_ids: list[int] | None = None,
    years: int = 2,
    inject_errors: bool = False,
    seed: int | None = None,
    assignment_rate: float = DEFAULT_ASSIGNMENT_RATE,
    max_team_members: int = DEFAULT_MAX_TEAM_MEMBERS,
    dashboard_url_base: str = DEFAULT_DASHBOARD_URL_BASE,
) -> pd.DataFrame:
    """Generate synthetic issue data.

    Args:
        count: Number of issues to generate
        project_ids: List of project IDs (default: [101, 102, 103])
        years: Years of history to simulate
        inject_errors: Whether to inject quality errors
        seed: Random seed for reproducibility
        assignment_rate: Ratio of issues assigned to a team member
        max_team_members: Maximum number of distinct team members
        dashboard_url_base: Base URL for locally opening seeded issues

    Returns:
        DataFrame with RawIssue schema
    """
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)
        Faker.seed(seed)

    if project_ids is None:
        project_ids = DEFAULT_PROJECT_IDS.copy()

    if not 0.0 <= assignment_rate <= 1.0:
        raise ValueError("assignment_rate must be between 0.0 and 1.0")

    if max_team_members < 1:
        raise ValueError("max_team_members must be at least 1")

    now = datetime.now()
    start_date = now - timedelta(days=years * 365)
    team_members = _build_team_members(max_team_members)
    assignees = _build_assignee_sequence(count, team_members, assignment_rate)

    issues: list[dict[str, object]] = []

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
        parent_id: int | None = None
        if work_item_type == "TASK" and random.random() < 0.9:
            # Sometimes reference existing issue, sometimes orphan
            if inject_errors and random.random() < 0.02:
                parent_id = 99999  # Zombie: non-existent parent
            elif i > 0:
                parent_id = 10000 + random.randint(0, max(0, i - 1))

        # Milestone generation
        milestone: str | None = None
        milestone_id: int | None = None
        milestone_due_date: datetime | None = None
        milestone_start_date: datetime | None = None

        if random.random() < 0.6:
            ms_ver = random.randint(1, 5)
            milestone = f"v1.{ms_ver}"
            milestone_id = 500 + ms_ver

            # Simulated schedule: v1.1 starts Jan 1st 2025, each lasts 30 days
            base_date = datetime(2025, 1, 1)
            ms_start = base_date + timedelta(days=(ms_ver - 1) * 30)
            ms_due = ms_start + timedelta(days=28)

            milestone_start_date = ms_start
            milestone_due_date = ms_due

        issue = {
            "id": issue_id,
            "iid": i + 1,
            "project_id": project_id,
            "title": _generate_title(labels),
            "description": _generate_description(labels),
            "state": state,
            "created_at": created_at,
            "updated_at": updated_at,
            "closed_at": closed_at,
            "labels": labels,
            "work_item_type": work_item_type,
            "parent_id": parent_id,
            "child_ids": [],
            "web_url": build_local_issue_url(project_id, i + 1, dashboard_url_base),
            "assignee": assignees[i],
            "milestone": milestone,
            "milestone_id": milestone_id,
            "milestone_due_date": milestone_due_date,
            "milestone_start_date": milestone_start_date,
        }
        issues.append(issue)

    # Post-processing: Populate child_ids
    # Create a quick lookup map
    issue_map = {issue["id"]: issue for issue in issues}

    for issue in issues:
        issue_parent_id = issue.get("parent_id")
        if isinstance(issue_parent_id, int) and issue_parent_id in issue_map:
            parent = issue_map[issue_parent_id]
            child_ids = parent.get("child_ids")
            if isinstance(child_ids, list):
                typed_child_ids = cast(list[int], child_ids)
            else:
                typed_child_ids = []
                parent["child_ids"] = typed_child_ids

            child_iid = issue.get("iid")
            if isinstance(child_iid, int):
                typed_child_ids.append(child_iid)  # linking by IID as per schema

    return pd.DataFrame(issues)


def build_local_issue_url(
    project_id: int,
    issue_iid: int,
    dashboard_url_base: str = DEFAULT_DASHBOARD_URL_BASE,
) -> str:
    """Build a local dashboard deep link for a synthetic issue."""
    base_url = dashboard_url_base.rstrip("/")
    query_string = urlencode(
        {
            "issue_source": "local",
            "issue_project_id": project_id,
            "issue_iid": issue_iid,
        }
    )
    return f"{base_url}/?{query_string}"


def _build_team_members(max_team_members: int) -> list[str]:
    """Create a bounded pool of realistic team-member usernames."""
    team_members: list[str] = []
    seen: set[str] = set()

    while len(team_members) < max_team_members:
        username = fake.user_name()
        if username in seen:
            continue
        seen.add(username)
        team_members.append(username)

    return team_members


def _build_assignee_sequence(
    count: int,
    team_members: list[str],
    assignment_rate: float,
) -> list[str | None]:
    """Build a deterministic-length assignee list for generated issues."""
    assignees: list[str | None] = [None] * count
    assigned_count = min(count, round(count * assignment_rate))

    if assigned_count == 0:
        return assignees

    assigned_indexes = random.sample(range(count), assigned_count)
    random.shuffle(assigned_indexes)

    guaranteed_members = team_members.copy()
    random.shuffle(guaranteed_members)
    guaranteed_count = min(len(guaranteed_members), assigned_count)

    for member, index in zip(
        guaranteed_members[:guaranteed_count],
        assigned_indexes[:guaranteed_count],
        strict=True,
    ):
        assignees[index] = member

    for index in assigned_indexes[guaranteed_count:]:
        assignees[index] = random.choice(team_members)

    return assignees


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
            # Context-specific templates
            "Investigate vulnerability report",  # for Security
            f"Review CVE-2024-{random.randint(1000,9999)}",
        ]

    # Inject keywords randomly for Context testing
    if random.random() < 0.3:
        keywords = ["Go", "SQL", "Postgres", "Database", "Vulnerability", "Exploit"]
        templates.append(f"{random.choice(keywords)}: {fake.sentence(nb_words=5)}")

    return random.choice(templates)


def _generate_description(labels: list[str]) -> str:
    """Generate a realistic issue description based on type."""
    if "type::bug" in labels:
        templates = [
            f"""## Bug Description
The {fake.word()} module is throwing an unexpected error when processing {fake.word()} requests.

### Steps to Reproduce
1. Navigate to the {fake.word()} page
2. Click on {fake.word()} button
3. Observe the error in console

### Expected Behavior
The system should {fake.sentence(nb_words=6)}

### Actual Behavior
Instead, we see: `ERROR: {fake.sentence(nb_words=4)}`

### Environment
- Version: {random.randint(1,5)}.{random.randint(0,9)}.{random.randint(0,99)}
- OS: {random.choice(['Linux', 'Windows', 'macOS'])}
""",
            f"""Error observed in production:
```
{fake.word().upper()}_ERROR: Failed to {fake.word()} the {fake.word()}
Stack trace:
  at {fake.word()}.{fake.word()}() line {random.randint(10, 500)}
  at {fake.word()}.{fake.word()}() line {random.randint(10, 500)}
```

This started occurring after the last deployment. Affects approximately {random.randint(1, 50)}% of users.
""",
        ]
    elif "type::feature" in labels:
        templates = [
            f"""## Feature Request

### Description
As a user, I want to be able to {fake.sentence(nb_words=6)} so that I can {fake.sentence(nb_words=5)}.

### Acceptance Criteria
- [ ] {fake.sentence(nb_words=6)}
- [ ] {fake.sentence(nb_words=5)}
- [ ] {fake.sentence(nb_words=4)}

### Technical Notes
This will require modifications to the {fake.word()} component.
""",
            f"""Implement {fake.word()} functionality to improve user experience.

**Business Value:** {fake.sentence(nb_words=8)}

**Technical Approach:**
1. Update the {fake.word()} API endpoint
2. Add new {fake.word()} validation
3. Modify the {fake.word()} component
""",
        ]
    else:
        templates = [
            f"""## Task Description

{fake.paragraph(nb_sentences=3)}

### Checklist
- [ ] Review {fake.word()} documentation
- [ ] Update {fake.word()} configuration
- [ ] Test changes in staging
""",
            f"""{fake.paragraph(nb_sentences=2)}

Related to: {fake.word()} refactoring initiative.
""",
        ]
    
    return random.choice(templates)


def seed_data(
    count: int = 1000,
    project_ids: list[int] | None = None,
    inject_errors: bool = False,
    output_path: Path = Path("data/processed"),
    seed: int | None = None,
    assignment_rate: float = DEFAULT_ASSIGNMENT_RATE,
    max_team_members: int = DEFAULT_MAX_TEAM_MEMBERS,
    dashboard_url_base: str = DEFAULT_DASHBOARD_URL_BASE,
) -> None:
    """Generate and save synthetic data to Parquet.

    Args:
        count: Number of issues to generate
        project_ids: List of project IDs
        inject_errors: Whether to inject quality errors
        output_path: Output directory for Parquet files
        seed: Random seed
        assignment_rate: Ratio of issues assigned to a team member
        max_team_members: Maximum number of distinct team members
        dashboard_url_base: Base URL for locally opening seeded issues
    """
    if project_ids is None:
        project_ids = DEFAULT_PROJECT_IDS.copy()

    output_path.mkdir(parents=True, exist_ok=True)

    logger.info(
        "Generating %s synthetic issues for projects %s "
        "(assignment_rate=%s, max_team_members=%s)",
        count,
        project_ids,
        assignment_rate,
        max_team_members,
    )

    df = generate_issues(
        count=count,
        project_ids=project_ids,
        inject_errors=inject_errors,
        seed=seed,
        assignment_rate=assignment_rate,
        max_team_members=max_team_members,
        dashboard_url_base=dashboard_url_base,
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
    parser.add_argument(
        "--assignment-rate",
        type=float,
        default=DEFAULT_ASSIGNMENT_RATE,
        help="Ratio of issues assigned to a team member (0.0 to 1.0)",
    )
    parser.add_argument(
        "--max-team-members",
        type=int,
        default=DEFAULT_MAX_TEAM_MEMBERS,
        help="Maximum number of distinct team members used as assignees",
    )
    parser.add_argument(
        "--dashboard-url-base",
        type=str,
        default=DEFAULT_DASHBOARD_URL_BASE,
        help="Base dashboard URL used for synthetic issue links",
    )
    args = parser.parse_args()

    project_ids = [int(p.strip()) for p in args.projects.split(",")]

    seed_data(
        count=args.count,
        project_ids=project_ids,
        inject_errors=args.inject_errors,
        output_path=Path(args.output),
        seed=args.seed,
        assignment_rate=args.assignment_rate,
        max_team_members=args.max_team_members,
        dashboard_url_base=args.dashboard_url_base,
    )

    print(f"\n✅ Generated {args.count} synthetic issues")
    print(f"   Projects: {project_ids}")
    print(f"   Errors injected: {args.inject_errors}")
    print(f"   Assignment rate: {args.assignment_rate}")
    print(f"   Max team members: {args.max_team_members}")
    print(f"   Dashboard URL base: {args.dashboard_url_base}")
    print(f"   Output: {args.output}/")


if __name__ == "__main__":
    main()
