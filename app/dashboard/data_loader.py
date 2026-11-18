"""Data loader for Layer 2 analytics Parquet files and sync metadata."""

import json
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

DEFAULT_ANALYTICS_PATH = Path("data/analytics")
DEFAULT_PROCESSED_PATH = Path("data/processed")
DEFAULT_STATE_PATH = Path("data/state/sync_state.json")

_ISSUE_DATE_COLUMNS = (
    "created_at",
    "updated_at",
    "closed_at",
    "milestone_due_date",
    "milestone_start_date",
)


def load_valid_issues(analytics_path: Path | None = None) -> pd.DataFrame:
    """Load valid issues from the Layer 2 analytics Parquet dataset."""
    base_path = analytics_path if analytics_path is not None else DEFAULT_ANALYTICS_PATH
    filepath = base_path / "issues_valid.parquet"

    if not filepath.exists():
        logger.warning("Valid issues file not found: %s", filepath)
        return pd.DataFrame()

    df = pd.read_parquet(filepath)

    if not df.empty and "priority" not in df.columns:
        df["priority"] = pd.NA

    for column in _ISSUE_DATE_COLUMNS:
        if column in df.columns:
            df[column] = pd.to_datetime(df[column], utc=True, errors="coerce")

    return df


def load_labels(processed_path: Path | None = None) -> dict[str, dict[str, str]]:
    """Load label color styles from Layer 1 processed Parquet files."""
    base_path = processed_path if processed_path is not None else DEFAULT_PROCESSED_PATH
    label_files = sorted(base_path.glob("labels_*.parquet"))
    label_styles: dict[str, dict[str, str]] = {}

    for filepath in label_files:
        try:
            df = pd.read_parquet(filepath)
        except Exception as exc:
            logger.warning("Failed to load labels from %s: %s", filepath, exc)
            continue

        if df.empty or "name" not in df.columns:
            continue

        colors = df["color"] if "color" in df.columns else pd.Series("#FFFFFF", index=df.index)
        text_colors = (
            df["text_color"]
            if "text_color" in df.columns
            else pd.Series("#000000", index=df.index)
        )
        deduped = pd.DataFrame(
            {
                "name": df["name"].astype(str),
                "color": colors.fillna("#FFFFFF").astype(str),
                "text_color": text_colors.fillna("#000000").astype(str),
            }
        ).drop_duplicates(subset=["name"], keep="last")

        for name, color, text_color in zip(
            deduped["name"].tolist(),
            deduped["color"].tolist(),
            deduped["text_color"].tolist(),
            strict=True,
        ):
            label_styles[name] = {"color": color, "text_color": text_color}

    return label_styles


def get_sync_status(state_path: Path | None = None) -> dict[str, str]:
    """Read the latest collector sync status from state JSON."""
    path = state_path if state_path is not None else DEFAULT_STATE_PATH
    if not path.exists():
        return {"status": "No sync data", "last_sync": "Never"}

    try:
        with path.open("r", encoding="utf-8") as handle:
            data: object = json.load(handle)
    except Exception as exc:
        logger.error("Failed to read sync state: %s", exc)
        return {"status": "Unknown", "last_sync": "Unknown"}

    if not isinstance(data, dict):
        return {"status": "Unknown", "last_sync": "Unknown"}

    projects = data.get("projects")
    if not isinstance(projects, dict) or not projects:
        return {"status": "No projects synced", "last_sync": "Never"}

    timestamps = [
        meta["last_sync_at"]
        for meta in projects.values()
        if isinstance(meta, dict) and isinstance(meta.get("last_sync_at"), str)
    ]
    if not timestamps:
        return {"status": f"{len(projects)} projects", "last_sync": "Never"}

    latest = max(timestamps)
    try:
        sync_dt = datetime.fromisoformat(latest.replace("Z", "+00:00"))
        formatted = sync_dt.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        formatted = latest

    return {"status": f"{len(projects)} projects", "last_sync": formatted}
