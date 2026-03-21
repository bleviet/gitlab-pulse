"""Interactive terminal manager for local synthetic project data."""

import argparse
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from app.processor.main import Processor
from tools.seeder import (
    DEFAULT_ASSIGNMENT_RATE,
    DEFAULT_DASHBOARD_URL_BASE,
    DEFAULT_MAX_TEAM_MEMBERS,
    seed_data,
)


@dataclass(frozen=True)
class LocalProjectSummary:
    """Summary of a locally seeded project parquet file."""

    project_id: int
    issue_count: int
    open_count: int
    closed_count: int
    assigned_count: int
    unique_assignees: int
    filepath: Path


def discover_local_projects(data_path: Path = Path("data")) -> list[LocalProjectSummary]:
    """Discover locally seeded projects from processed parquet files.

    Args:
        data_path: Base data directory.

    Returns:
        Summaries for all detected local issue parquet files.
    """
    processed_path = data_path / "processed"
    summaries: list[LocalProjectSummary] = []

    for filepath in sorted(processed_path.glob("issues_*.parquet")):
        project_id = _extract_project_id(filepath)
        if project_id is None:
            continue

        df = pd.read_parquet(filepath)
        assigned_series = df["assignee"] if "assignee" in df.columns else pd.Series(dtype="object")
        state_series = df["state"] if "state" in df.columns else pd.Series(dtype="object")

        summaries.append(
            LocalProjectSummary(
                project_id=project_id,
                issue_count=len(df),
                open_count=int((state_series == "opened").sum()),
                closed_count=int((state_series == "closed").sum()),
                assigned_count=int(assigned_series.notna().sum()),
                unique_assignees=int(assigned_series.dropna().nunique()),
                filepath=filepath,
            )
        )

    return summaries


def delete_local_projects(
    project_ids: list[int],
    data_path: Path = Path("data"),
    clear_analytics: bool = False,
    clear_state: bool = False,
) -> list[Path]:
    """Delete local parquet files for the given project IDs.

    Args:
        project_ids: Project IDs to remove.
        data_path: Base data directory.
        clear_analytics: Whether to remove analytics parquet outputs.
        clear_state: Whether to remove collector sync state.

    Returns:
        Paths that were removed.
    """
    removed_paths: list[Path] = []
    processed_path = data_path / "processed"

    for project_id in project_ids:
        for prefix in ("issues", "milestones", "labels"):
            filepath = processed_path / f"{prefix}_{project_id}.parquet"
            if filepath.exists():
                filepath.unlink()
                removed_paths.append(filepath)

    if clear_analytics:
        analytics_path = data_path / "analytics"
        for filepath in sorted(analytics_path.glob("*.parquet")):
            filepath.unlink()
            removed_paths.append(filepath)

    if clear_state:
        state_path = data_path / "state" / "sync_state.json"
        if state_path.exists():
            state_path.unlink()
            removed_paths.append(state_path)

    return removed_paths


def rebuild_analytics(
    data_path: Path = Path("data"),
    rules_path: Path = Path("app/config/rules"),
) -> dict[str, int]:
    """Rebuild Layer 2 analytics from local processed files."""
    processor = Processor(data_path=data_path, rules_path=rules_path)
    return processor.process_all()


def print_project_table(projects: list[LocalProjectSummary]) -> None:
    """Print a compact summary table for detected local projects."""
    if not projects:
        print("\nNo local projects detected in data/processed.")
        return

    print("\nDetected local projects:")
    print("project_id | issues | opened | closed | assigned | unique_assignees | file")
    print("-" * 88)
    for project in projects:
        print(
            f"{project.project_id:<10} | "
            f"{project.issue_count:<6} | "
            f"{project.open_count:<6} | "
            f"{project.closed_count:<6} | "
            f"{project.assigned_count:<8} | "
            f"{project.unique_assignees:<16} | "
            f"{project.filepath}"
        )


def run_seed_action(
    project_ids: list[int],
    count: int,
    inject_errors: bool,
    seed: int | None,
    assignment_rate: float,
    max_team_members: int,
    dashboard_url_base: str,
    data_path: Path = Path("data"),
) -> None:
    """Create or reseed local projects."""
    seed_data(
        count=count,
        project_ids=project_ids,
        inject_errors=inject_errors,
        output_path=data_path / "processed",
        seed=seed,
        assignment_rate=assignment_rate,
        max_team_members=max_team_members,
        dashboard_url_base=dashboard_url_base,
    )


def run_reset_action(
    project_ids: list[int],
    count: int,
    inject_errors: bool,
    seed: int | None,
    assignment_rate: float,
    max_team_members: int,
    dashboard_url_base: str,
    data_path: Path = Path("data"),
    rules_path: Path = Path("app/config/rules"),
) -> dict[str, int]:
    """Delete selected project data, reseed it, and rebuild analytics."""
    delete_local_projects(
        project_ids=project_ids,
        data_path=data_path,
        clear_analytics=True,
        clear_state=True,
    )
    run_seed_action(
        project_ids=project_ids,
        count=count,
        inject_errors=inject_errors,
        seed=seed,
        assignment_rate=assignment_rate,
        max_team_members=max_team_members,
        dashboard_url_base=dashboard_url_base,
        data_path=data_path,
    )
    return rebuild_analytics(data_path=data_path, rules_path=rules_path)


def main() -> None:
    """CLI entry point for the local data manager."""
    parser = argparse.ArgumentParser(description="Manage local synthetic project data")
    parser.add_argument(
        "--action",
        choices=["menu", "list", "seed", "delete", "delete-all", "process", "reset"],
        default="menu",
        help="Action to run. Defaults to interactive menu.",
    )
    parser.add_argument("--project-ids", type=str, help="Comma-separated project IDs")
    parser.add_argument("--count", type=int, default=1000, help="Number of synthetic issues to generate")
    parser.add_argument("--inject-errors", action="store_true", help="Inject quality errors during seeding")
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
    parser.add_argument("--data-path", type=str, default="data", help="Base data directory")
    parser.add_argument("--rules-path", type=str, default="app/config/rules", help="Rules directory")
    parser.add_argument("--clear-analytics", action="store_true", help="Also remove analytics parquet output")
    parser.add_argument("--clear-state", action="store_true", help="Also remove collector sync state")
    args = parser.parse_args()

    data_path = Path(args.data_path)
    rules_path = Path(args.rules_path)

    if args.action == "menu":
        run_interactive_menu(data_path=data_path, rules_path=rules_path)
        return

    project_ids = _parse_project_ids(args.project_ids) if args.project_ids else []

    if args.action == "list":
        print_project_table(discover_local_projects(data_path))
        return

    if args.action == "process":
        results = rebuild_analytics(data_path=data_path, rules_path=rules_path)
        print(f"\nProcessing complete: {results['valid']} valid, {results['quality']} quality issues")
        return

    if args.action == "delete-all":
        detected_project_ids = [project.project_id for project in discover_local_projects(data_path)]
        removed = delete_local_projects(
            project_ids=detected_project_ids,
            data_path=data_path,
            clear_analytics=args.clear_analytics,
            clear_state=args.clear_state,
        )
        _print_removed_paths(removed)
        return

    if not project_ids:
        raise ValueError("--project-ids is required for this action")

    if args.action == "seed":
        run_seed_action(
            project_ids=project_ids,
            count=args.count,
            inject_errors=args.inject_errors,
            seed=args.seed,
            assignment_rate=args.assignment_rate,
            max_team_members=args.max_team_members,
            dashboard_url_base=args.dashboard_url_base,
            data_path=data_path,
        )
        print_project_table(discover_local_projects(data_path))
        return

    if args.action == "delete":
        removed = delete_local_projects(
            project_ids=project_ids,
            data_path=data_path,
            clear_analytics=args.clear_analytics,
            clear_state=args.clear_state,
        )
        _print_removed_paths(removed)
        return

    if args.action == "reset":
        results = run_reset_action(
            project_ids=project_ids,
            count=args.count,
            inject_errors=args.inject_errors,
            seed=args.seed,
            assignment_rate=args.assignment_rate,
            max_team_members=args.max_team_members,
            dashboard_url_base=args.dashboard_url_base,
            data_path=data_path,
            rules_path=rules_path,
        )
        print_project_table(discover_local_projects(data_path))
        print(f"\nProcessing complete: {results['valid']} valid, {results['quality']} quality issues")


def run_interactive_menu(
    data_path: Path = Path("data"),
    rules_path: Path = Path("app/config/rules"),
) -> None:
    """Run the interactive terminal menu for local data management."""
    while True:
        projects = discover_local_projects(data_path)
        print("\nLocal Data Manager")
        print("==================")
        print("1. List detected local projects")
        print("2. Create or reseed local projects")
        print("3. Delete selected local projects")
        print("4. Delete all detected local projects")
        print("5. Rebuild analytics")
        print("6. Reset, reseed, and rebuild analytics")
        print("7. Exit")

        choice = input("Select an option: ").strip()

        if choice == "1":
            print_project_table(projects)
        elif choice == "2":
            seed_options = _prompt_seed_options(projects)
            run_seed_action(
                project_ids=seed_options.project_ids,
                count=seed_options.count,
                inject_errors=seed_options.inject_errors,
                seed=seed_options.seed,
                assignment_rate=seed_options.assignment_rate,
                max_team_members=seed_options.max_team_members,
                dashboard_url_base=seed_options.dashboard_url_base,
                data_path=data_path,
            )
            print_project_table(discover_local_projects(data_path))
        elif choice == "3":
            project_ids = _prompt_project_ids(projects)
            removed = delete_local_projects(project_ids=project_ids, data_path=data_path)
            _print_removed_paths(removed)
        elif choice == "4":
            detected_project_ids = [project.project_id for project in projects]
            removed = delete_local_projects(
                project_ids=detected_project_ids,
                data_path=data_path,
                clear_analytics=_prompt_bool("Also clear analytics output?", default=True),
                clear_state=_prompt_bool("Also clear collector sync state?", default=True),
            )
            _print_removed_paths(removed)
        elif choice == "5":
            results = rebuild_analytics(data_path=data_path, rules_path=rules_path)
            print(f"\nProcessing complete: {results['valid']} valid, {results['quality']} quality issues")
        elif choice == "6":
            seed_options = _prompt_seed_options(projects)
            results = run_reset_action(
                project_ids=seed_options.project_ids,
                count=seed_options.count,
                inject_errors=seed_options.inject_errors,
                seed=seed_options.seed,
                assignment_rate=seed_options.assignment_rate,
                max_team_members=seed_options.max_team_members,
                dashboard_url_base=seed_options.dashboard_url_base,
                data_path=data_path,
                rules_path=rules_path,
            )
            print_project_table(discover_local_projects(data_path))
            print(f"\nProcessing complete: {results['valid']} valid, {results['quality']} quality issues")
        elif choice == "7":
            print("Goodbye.")
            return
        else:
            print("Invalid option. Please choose 1-7.")


@dataclass(frozen=True)
class SeedOptions:
    """Interactive or CLI seed configuration."""

    project_ids: list[int]
    count: int
    inject_errors: bool
    seed: int | None
    assignment_rate: float
    max_team_members: int
    dashboard_url_base: str


def _prompt_seed_options(projects: list[LocalProjectSummary]) -> SeedOptions:
    """Prompt for seeding options."""
    default_project_ids = ",".join(str(project.project_id) for project in projects) or "101,102,103"
    project_ids = _parse_project_ids(input(f"Project IDs [{default_project_ids}]: ").strip() or default_project_ids)
    count = _prompt_int("Issue count", default=1000, minimum=1)
    inject_errors = _prompt_bool("Inject quality errors?", default=False)
    seed_value = input("Random seed [blank for random]: ").strip()
    seed = int(seed_value) if seed_value else None
    assignment_rate = _prompt_float(
        "Assignment rate (0.0 to 1.0)",
        default=DEFAULT_ASSIGNMENT_RATE,
        minimum=0.0,
        maximum=1.0,
    )
    max_team_members = _prompt_int("Max team members", default=DEFAULT_MAX_TEAM_MEMBERS, minimum=1)
    dashboard_url_base = (
        input(f"Dashboard URL base [{DEFAULT_DASHBOARD_URL_BASE}]: ").strip()
        or DEFAULT_DASHBOARD_URL_BASE
    )
    return SeedOptions(
        project_ids=project_ids,
        count=count,
        inject_errors=inject_errors,
        seed=seed,
        assignment_rate=assignment_rate,
        max_team_members=max_team_members,
        dashboard_url_base=dashboard_url_base,
    )


def _prompt_project_ids(projects: list[LocalProjectSummary]) -> list[int]:
    """Prompt for project IDs using detected projects as defaults."""
    default_project_ids = ",".join(str(project.project_id) for project in projects)
    if not default_project_ids:
        raise ValueError("No local projects detected.")
    raw_value = input(f"Project IDs [{default_project_ids}]: ").strip() or default_project_ids
    return _parse_project_ids(raw_value)


def _prompt_bool(prompt: str, default: bool) -> bool:
    """Prompt for a yes/no value."""
    default_value = "Y/n" if default else "y/N"
    raw_value = input(f"{prompt} [{default_value}]: ").strip().lower()
    if not raw_value:
        return default
    return raw_value in {"y", "yes"}


def _prompt_int(prompt: str, default: int, minimum: int) -> int:
    """Prompt for an integer value."""
    raw_value = input(f"{prompt} [{default}]: ").strip()
    value = int(raw_value) if raw_value else default
    if value < minimum:
        raise ValueError(f"{prompt} must be at least {minimum}")
    return value


def _prompt_float(prompt: str, default: float, minimum: float, maximum: float) -> float:
    """Prompt for a float value."""
    raw_value = input(f"{prompt} [{default}]: ").strip()
    value = float(raw_value) if raw_value else default
    if not minimum <= value <= maximum:
        raise ValueError(f"{prompt} must be between {minimum} and {maximum}")
    return value


def _extract_project_id(filepath: Path) -> int | None:
    """Extract project ID from an issue parquet filename."""
    try:
        return int(filepath.stem.split("_", maxsplit=1)[1])
    except (IndexError, ValueError):
        return None


def _parse_project_ids(raw_value: str) -> list[int]:
    """Parse comma-separated project IDs."""
    project_ids = [int(value.strip()) for value in raw_value.split(",") if value.strip()]
    if not project_ids:
        raise ValueError("At least one project ID is required")
    return project_ids


def _print_removed_paths(removed_paths: list[Path]) -> None:
    """Print deleted paths."""
    if not removed_paths:
        print("\nNo matching local files were removed.")
        return

    print("\nRemoved:")
    for filepath in removed_paths:
        print(f"- {filepath}")


if __name__ == "__main__":
    main()
