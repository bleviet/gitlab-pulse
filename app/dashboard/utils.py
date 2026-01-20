import pandas as pd

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

    # Build adjacency list
    # Use string mapping for safety (NaN handling)
    children_map = {}
    roots = []
    
    # Pre-compute lookups
    all_ids = set(df[id_col])
    
    for idx, row in df.iterrows():
        pid = row[parent_col]
        iid = row[id_col]
        
        # If parent is NaN or not in the current dataset, treat as root
        if pd.isna(pid) or pid not in all_ids:
            roots.append(idx)
        else:
            if pid not in children_map:
                children_map[pid] = []
            children_map[pid].append(idx)
            
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
    hierarchy_levels = {x[0]: x[1] for x in ordered_indices}
    
    sorted_df = df.loc[new_order].copy()
    
    # Apply Indentation
    # Using non-breaking spaces or arrow
    def indent_title(row):
        level = hierarchy_levels.get(row.name, 0)
        if level > 0:
            prefix = "&nbsp;&nbsp;&nbsp;&nbsp;" * level + "↳ " # Markdown/HTML friendly?
            # Streamlit st.dataframe supports limited HTML if configured, but st.column_config.TextColumn does not.
            # Plain unicode is safer.
            prefix = "    " * level + "↳ "
            return prefix + str(row[title_col])
        return str(row[title_col])
        
    sorted_df[title_col] = sorted_df.apply(indent_title, axis=1)
    
    sorted_df[title_col] = sorted_df.apply(indent_title, axis=1)
    
    return sorted_df


def get_semantic_color(key: str, default: str = "#64748B") -> str:
    """Get a semantic color for the dashboard.
    
    This is a placeholder. In a real app, this might read from st.session_state 
    if loaded from config, or just return defaults.
    """
    # Simple hardcoded fallback or read from a global if accessible
    COLORS = {
        "active": "#3B82F6",
        "waiting": "#F59E0B",
        "completed": "#10B981",
        "Unassigned": "#94A3B8",
    }
    return COLORS.get(key, default)
