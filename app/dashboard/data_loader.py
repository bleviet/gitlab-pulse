"""Data loader with caching for Layer 3 Dashboard.

Uses Streamlit's @st.cache_data for efficient data loading.
"""

import logging
from pathlib import Path
from typing import Optional

import pandas as pd
import streamlit as st

logger = logging.getLogger(__name__)

# Default data paths
DEFAULT_ANALYTICS_PATH = Path("data/analytics")


@st.cache_data(ttl=120)  # 2-minute cache
def load_valid_issues(analytics_path: Optional[str] = None) -> pd.DataFrame:
    """Load valid issues from analytics Parquet.

    Args:
        analytics_path: Path to analytics directory

    Returns:
        DataFrame with valid issues
    """
    path = Path(analytics_path) if analytics_path else DEFAULT_ANALYTICS_PATH
    filepath = path / "issues_valid.parquet"

    if not filepath.exists():
        logger.warning(f"Valid issues file not found: {filepath}")
        return pd.DataFrame()

    df = pd.read_parquet(filepath)

    # Ensure datetime columns are proper types
    for col in ["created_at", "updated_at", "closed_at"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], utc=True)

    # Convert category columns for memory efficiency
    for col in ["state", "work_item_type", "issue_type", "severity", "team"]:
        if col in df.columns:
            df[col] = df[col].astype("category")

    logger.info(f"Loaded {len(df)} valid issues")
    return df


@st.cache_data(ttl=120)
def load_quality_issues(analytics_path: Optional[str] = None) -> pd.DataFrame:
    """Load quality (failed) issues from analytics Parquet.

    Args:
        analytics_path: Path to analytics directory

    Returns:
        DataFrame with quality issues
    """
    path = Path(analytics_path) if analytics_path else DEFAULT_ANALYTICS_PATH
    filepath = path / "data_quality.parquet"

    if not filepath.exists():
        logger.warning(f"Quality issues file not found: {filepath}")
        return pd.DataFrame()

    df = pd.read_parquet(filepath)
    logger.info(f"Loaded {len(df)} quality issues")
    return df


# Default processed path for milestones (Layer 1 output)
DEFAULT_PROCESSED_PATH = Path("data/processed")


@st.cache_data(ttl=120)
def load_milestones(processed_path: Optional[str] = None) -> pd.DataFrame:
    """Load milestones from processed Parquet files.

    Combines milestones from all project files.

    Args:
        processed_path: Path to processed directory

    Returns:
        DataFrame with all milestones
    """
    path = Path(processed_path) if processed_path else DEFAULT_PROCESSED_PATH

    # Find all milestone files
    milestone_files = list(path.glob("milestones_*.parquet"))

    if not milestone_files:
        logger.warning("No milestone files found")
        return pd.DataFrame()

    # Load and combine all milestone files
    dfs = []
    for filepath in milestone_files:
        try:
            df = pd.read_parquet(filepath)
            dfs.append(df)
        except Exception as e:
            logger.warning(f"Failed to load {filepath}: {e}")

    if not dfs:
        return pd.DataFrame()

    combined = pd.concat(dfs, ignore_index=True)

    # Ensure datetime columns are proper types
    for col in ["due_date", "start_date", "created_at", "updated_at"]:
        if col in combined.columns:
            combined[col] = pd.to_datetime(combined[col], utc=True)

    # Convert state to category
    if "state" in combined.columns:
        combined["state"] = combined["state"].astype("category")

    logger.info(f"Loaded {len(combined)} milestones from {len(milestone_files)} files")
    return combined


def get_sync_status(state_path: Optional[str] = None) -> dict[str, str]:
    """Get the last sync status from state file.

    Args:
        state_path: Path to sync state file

    Returns:
        Dict with sync status info
    """
    import json
    from datetime import datetime

    path = Path(state_path) if state_path else Path("data/state/sync_state.json")

    if not path.exists():
        return {"status": "No sync data", "last_sync": "Never"}

    try:
        with path.open("r") as f:
            data = json.load(f)

        # Find the most recent sync
        projects = data.get("projects", {})
        if not projects:
            return {"status": "No projects synced", "last_sync": "Never"}

        last_sync = max(
            (p.get("last_sync_at") for p in projects.values() if p.get("last_sync_at")),
            default=None,
        )

        if last_sync:
            sync_dt = datetime.fromisoformat(last_sync.replace("Z", "+00:00"))
            return {
                "status": f"{len(projects)} projects",
                "last_sync": sync_dt.strftime("%Y-%m-%d %H:%M"),
            }

    except Exception as e:
        logger.error(f"Failed to read sync state: {e}")

    return {"status": "Unknown", "last_sync": "Unknown"}


def filter_by_date_range(
    df: pd.DataFrame,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
) -> pd.DataFrame:
    """Filter DataFrame by created_at date range.

    Args:
        df: DataFrame to filter
        start_date: Start of range
        end_date: End of range

    Returns:
        Filtered DataFrame
    """
    if df.empty:
        return df

    mask = (df["created_at"] >= start_date) & (df["created_at"] <= end_date)
    return df[mask]


def filter_by_team(df: pd.DataFrame, team: str) -> pd.DataFrame:
    """Filter DataFrame by team.

    Args:
        df: DataFrame to filter
        team: Team name (or "All" for no filter)

    Returns:
        Filtered DataFrame
    """
    if df.empty or team == "All":
        return df

    return df[df["team"] == team]


def filter_by_context(df: pd.DataFrame, context: str) -> pd.DataFrame:
    """Filter DataFrame by context (sub-project).

    Args:
        df: DataFrame to filter
        context: Context name (or "All" for no filter)

    Returns:
        Filtered DataFrame
    """
    if df.empty or context == "All":
        return df

    if "context" not in df.columns:
        return df

    return df[df["context"] == context]


def filter_by_milestone(df: pd.DataFrame, milestone: str) -> pd.DataFrame:
    """Filter DataFrame by milestone.

    Args:
        df: DataFrame to filter
        milestone: Milestone title (or "All" for no filter)

    Returns:
        Filtered DataFrame
    """
    if df.empty or milestone == "All":
        return df

    if "milestone" not in df.columns:
        return df

    # Handle cases where milestone might be NaN but we want specific matches
    # This filter assumes strictly matching the milestone title
    return df[df["milestone"] == milestone]


@st.cache_data(ttl=3600)  # 1-hour cache for labels (they change rarely)
def load_labels(processed_path: Optional[str] = None) -> dict[str, dict[str, str]]:
    """Load label colors from processed Parquet files.

    Args:
        processed_path: Path to processed directory

    Returns:
        Dict mapping label name to style dict {'color': hex, 'text_color': hex}
    """
    path = Path(processed_path) if processed_path else DEFAULT_PROCESSED_PATH

    label_files = list(path.glob("labels_*.parquet"))
    
    label_styles = {}
    if not label_files:
        return label_styles

    for filepath in label_files:
        try:
            df = pd.read_parquet(filepath)
            if not df.empty and "name" in df.columns:
                # Ensure columns exist
                if "color" not in df.columns:
                    df["color"] = "#FFFFFF"
                if "text_color" not in df.columns:
                    df["text_color"] = "#000000" # Default black text if missing

                # Deduplicate by name (last wins)
                df = df.drop_duplicates(subset=["name"], keep="last")
                
                # Convert to dict: name -> {color: ..., text_color: ...}
                batch = df.set_index("name")[["color", "text_color"]].to_dict(orient="index")
                label_styles.update(batch)
        except Exception as e:
            logger.warning(f"Failed to load labels from {filepath}: {e}")

    logger.info(f"Loaded styles for {len(label_styles)} labels")
    return label_styles
