import pandas as pd

from app.dashboard.theme import get_palette


def normalize_assignee_labels(series: pd.Series) -> pd.Series:
    """Normalize assignee values for display and filtering."""
    return (
        series.fillna("Unassigned")
        .astype(str)
        .str.strip()
        .replace(
            {
                "": "Unassigned",
                "nan": "Unassigned",
                "<NA>": "Unassigned",
                "None": "Unassigned",
            }
        )
    )


def sort_hierarchy(df: pd.DataFrame, parent_col: str = "parent_id", id_col: str = "id", title_col: str = "title") -> pd.DataFrame:
    """Sort DataFrame hierarchically: Parent followed by Children.

    Also modifies the `title_col` to add indentation for children.

    Args:
        df: Input DataFrame.
        parent_col: Column containing parent ID.
        id_col: Column containing item ID.
        title_col: Column containing the title to indent.

    Returns:
        Sorted and indented DataFrame.
    """
    if df.empty or parent_col not in df.columns:
        return df

    # Build adjacency list using vectorized operations (avoids iterrows)
    children_map: dict[object, list[object]] = {}

    all_ids = set(df[id_col])
    parent_series = df[parent_col]
    is_root = parent_series.isna() | ~parent_series.isin(all_ids)
    roots = df.index[is_root].tolist()

    child_df = df[~is_root]
    for idx, pid in zip(child_df.index, child_df[parent_col]):
        children_map.setdefault(pid, []).append(idx)

    # DFS Traversal to build new order
    ordered_indices = []

    def dfs(idx, level):
        ordered_indices.append((idx, level))
        row_id = df.loc[idx, id_col]

        children = children_map.get(row_id, [])
        # Sort children safely? Maybe by ID or Title?
        # For now, stable sort order from original DF is preserved by iterrows order

        for child_idx in children:
            dfs(child_idx, level + 1)

    for root_idx in roots:
        dfs(root_idx, 0)

    # Reconstruct DataFrame
    if not ordered_indices:
        return df

    new_order = [x[0] for x in ordered_indices]

    sorted_df = df.loc[new_order].copy()

    # Apply Indentation directly using list comprehension for efficiency
    # This avoids the overhead of .apply() and fixes the double-indentation bug
    def _format_title(title, level):
        if level > 0:
            # Using plain spaces and arrow for clear visual hierarchy
            prefix = "    " * level + "↳ "
            return f"{prefix}{title}"
        return str(title)

    new_titles = [
        _format_title(df.at[idx, title_col], level)
        for idx, level in ordered_indices
    ]

    sorted_df[title_col] = new_titles

    return sorted_df


def get_semantic_color(key: str, default: str = "#64748B") -> str:
    """Get a semantic color for the dashboard.

    Uses the centralized theme palette as the single source of truth.

    Args:
        key: Color key name (e.g., "active", "waiting").
        default: Fallback color hex string.

    Returns:
        Hex color string.
    """
    return get_palette().get(key, default)
