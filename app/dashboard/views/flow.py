"""Flow Page (Value Stream) for Layer 3 Dashboard.

Visualizes flow efficiency, bottlenecks, and aging.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from app.dashboard.utils import sort_hierarchy

# Semantic color palette
COLORS = {
    "primary": "#4F46E5",
    "active": "#3B82F6",
    "waiting": "#F59E0B",
    "completed": "#10B981",
    "neutral": "#64748B",
}


def render_flow_view(
    df: pd.DataFrame, 
    colors: dict[str, str] | None = None,
    stage_descriptions: dict[str, str] | None = None
) -> None:
    """Render the Flow (Value Stream) page.

    Args:
        df: Filtered DataFrame with valid issues
        colors: Optional dictionary of semantic colors to override defaults
        stage_descriptions: Optional mapping of stage names to description strings
    """
    if colors:
        COLORS.update(colors)

    st.header("🌊 Development Value Stream")
    st.caption("Flow metrics: Inventory, Staleness, and Efficiency")

    # Filter out empty stages or irrelevant data if needed
    # But for flow, we usually want to see everything
    if df.empty:
        st.warning("No data available.")
        return

    # Deduplicate for global metrics and charts to avoid double counting
    # Multi-context issues appear as multiple rows in 'df' (one per context)
    # We want to count the issue only once for WIP, Efficiency, and Charts
    if "id" in df.columns:
        unique_df = df.drop_duplicates(subset=["id"])
    else:
        unique_df = df

    # Top Row: Metrics (Use unique issues)
    _render_flow_metrics(unique_df)

    # Charts (Collapsible)
    with st.expander("📊 Flow Charts", expanded=True):
        tab1, tab2 = st.tabs(["🔻 Project Funnel", "⏳ Stage Stickiness"])
        
        with tab1:
            # Use unique issues for funnel to show correct counts
            funnel_selection = _render_funnel_chart(unique_df, stage_descriptions)
            
        with tab2:
            # Use unique issues for aging to show distinct items
            aging_selection = _render_aging_chart(unique_df)

    # Apply interactive filters (Apply to original DF which allows exploring contexts)
    filtered_df = df.copy()

    # Filter by Funnel Selection
    if funnel_selection and funnel_selection.get("selection", {}).get("points"):
        selected_points = funnel_selection["selection"]["points"]
        # Extract filters: stage and severity
        # We perform an OR filter for multiple selected points
        masks = []
        for point in selected_points:
            # Point has customdata or y (stage) and legend group/color (severity)
            # px.bar with orientation h: y is stage, color is severity
            # customdata is likely needed to be robust
            stage = point.get("y")
            severity = point.get("customdata", [None])[0] # customdata[0] is severity if we add it

            mask = (filtered_df["stage"] == stage)
            if severity:
                 # Normalize severity for comparison to match the chart's logic
                 # The chart uses Title Case for all severities, and "Unset" for NaNs

                 if severity == "Unset":
                     # Match "Unset", NaNs, None, empty strings
                     mask &= (
                         filtered_df["severity"].isna() |
                         (filtered_df["severity"].astype(str).str.strip().str.lower().isin(["unset", "none", "nan", "<na>", ""]))
                     )
                 else:
                     # Match severity (case-insensitive to be safe)
                     mask &= (filtered_df["severity"].astype(str).str.strip().str.lower() == severity.lower())

            masks.append(mask)

        if masks:
            final_mask = pd.Series(False, index=filtered_df.index)
            for m in masks:
                final_mask |= m
            filtered_df = filtered_df[final_mask]

    # Filter by Aging Selection (Intersection with Funnel)
    if aging_selection and aging_selection.get("selection", {}).get("points"):
        selected_points = aging_selection["selection"]["points"]
        # Aging chart: x=stage, y=days_in_stage, color=stage_type
        # We filter by stage (x). Days is continuous, so selecting a point usually implies interest in that item or stage.
        # But boxplots selection might be selecting outliers?
        # Let's assume selecting points filters by Stage of those points.
        selected_stages = {p.get("x") for p in selected_points}
        if selected_stages:
            filtered_df = filtered_df[filtered_df["stage"].isin(selected_stages)]

    # Detail grid (Collapsible)
    with st.expander("📋 Issue Details", expanded=True):
        _render_issue_detail_grid(filtered_df)


def _render_flow_metrics(df: pd.DataFrame) -> None:
    """Render Flow key metrics.

    Args:
        df: DataFrame of issues (should be unique/deduplicated)
    """
    col1, col2, col3, col4 = st.columns(4)

    # 1. Active WIP
    active_mask = df["stage_type"] == "active"
    active_count = len(df[active_mask])

    with col1:
        st.metric("Active WIP", active_count, help="Issues in active stages")

    # 2. Flow Efficiency
    total_wip = len(df[df["stage_type"].isin(["active", "waiting"])])
    if total_wip > 0:
        efficiency = round((active_count / total_wip) * 100, 1)
    else:
        efficiency = 0

    with col2:
        st.metric(
            "Flow Efficiency",
            f"{efficiency}%",
            help="Active / (Active + Waiting)"
        )

    # 3. Bottleneck (Max WIP Stage that is NOT Done)
    # Exclude 'completed' stage types usually for bottleneck analysis
    wip_df = df[df["stage_type"] != "completed"]
    if not wip_df.empty:
        stage_counts = wip_df["stage"].value_counts()
        bottleneck_stage = stage_counts.idxmax()
        bottleneck_count = stage_counts.max()
    else:
        bottleneck_stage = "None"
        bottleneck_count = 0

    with col3:
        st.metric("Top Bottleneck", bottleneck_stage, f"{bottleneck_count} items")

    # 4. Max Staleness
    max_days = df["days_in_stage"].max() if not df.empty else 0
    with col4:
        st.metric("Max Staleness", f"{max_days} days", help="Longest time in current stage")



def _render_funnel_chart(
    df: pd.DataFrame, 
    stage_descriptions: dict[str, str] | None = None
) -> dict | None:
    """Render horizontal bar chart of issues per stage (The Funnel).

    Returns:
        Selection state dictionary or None
    """
    total_issues = len(df)
    help_text = (
        "**Interaction Guide:**\n"
        "- **Hover** to view stage descriptions.\n"
        "- **Click** a bar segment to filter the Issue Drill-down below.\n"
        "- **Shift+Click** to select multiple segments for combined filtering.\n"
        "- **Double-Click** to reset selection."
    )
    st.subheader(f"🔻 Project Funnel (Total: {total_issues})", help=help_text)

    # Check if severity column exists for stacked view
    has_severity = "severity" in df.columns

    # Calculate totals per stage for the labels
    # We want these to appear at the end of the bars
    stage_totals = df.groupby("stage", observed=True).size().reset_index(name="total_count")

    if has_severity:
        # Fill NaN severity with "Unset" for display
        # Convert to string first to handle Categorical dtype
        df_chart = df.copy()

        # Normalize severity: handle NaNs, convert to string, strip whitespace, and title case
        # This fixes issues where "Critical" and "critical " might be treated as different
        df_chart["severity"] = (
            df_chart["severity"]
            .astype(str)
            .replace("nan", "Unset")
            .replace("<NA>", "Unset")
            .replace("None", "Unset")
            .str.strip()
            .str.title()
        )
        # Ensure "Unset" remains "Unset" (title() handles it, but just to be sure if lowercased)

        # Consolidate stage_order: use the minimum order for each stage to prevent splitting
        # This handles cases where different rules assign different orders to the same stage name
        stage_order_map = df_chart.groupby("stage")["stage_order"].min()
        df_chart["stage_order"] = df_chart["stage"].map(stage_order_map)

        # Prepare stage order for plotting
        stage_order_df = df_chart[["stage", "stage_order"]].drop_duplicates().sort_values("stage_order")
        sorted_stages = stage_order_df["stage"].tolist()

        # Aggregation with severity breakdown
        stage_stats = df_chart.groupby(["stage", "stage_order", "severity"]).size().reset_index(name="count")
        
        # Add description to stage_stats
        if stage_descriptions:
            stage_stats["description"] = stage_stats["stage"].map(stage_descriptions).fillna("")
        else:
            stage_stats["description"] = ""
        
        # Calculate severity counts for legend labels
        severity_counts = df_chart["severity"].value_counts()
        severity_label_map = {
            sev: f"{sev} ({count})" 
            for sev, count in severity_counts.items()
        }
        
        # Add formatted label column
        stage_stats["severity_label"] = stage_stats["severity"].map(severity_label_map)

        # Sort by defined order
        stage_stats = stage_stats.sort_values("stage_order")

        if stage_stats.empty:
            st.info("No stage data.")
            return

        # Define priority color palette (semantic)
        priority_colors = {
            "Critical": COLORS.get("critical", "#EF4444"),
            "High": COLORS.get("high", "#F97316"),
            "Medium": COLORS.get("medium", "#EAB308"),
            "Low": COLORS.get("low", "#22C55E"),
            "Unset": COLORS.get("unset", "#94A3B8"),
        }
        
        # Construct color map and order for formatted labels
        final_color_map = {}
        ordered_severity_labels = []
        base_severity_order = ["Critical", "High", "Medium", "Low", "Unset"]
        
        for sev in base_severity_order:
            if sev in severity_label_map:
                label = severity_label_map[sev]
                ordered_severity_labels.append(label)
                final_color_map[label] = priority_colors.get(sev, priority_colors["Unset"])
                
        # Handle any other severities
        for sev, label in severity_label_map.items():
            if label not in final_color_map:
                ordered_severity_labels.append(label)
                final_color_map[label] = priority_colors.get("Unset")

        fig = px.bar(
            stage_stats,
            x="count",
            y="stage",
            color="severity_label", # Use formatted label for legend
            orientation="h",
            text="count",
            title="",
            color_discrete_map=final_color_map,
            category_orders={
                "severity_label": ordered_severity_labels,
                "stage": sorted_stages
            },
            custom_data=["severity", "description"], # Include description
        )

        fig.update_traces(
            textposition="inside", 
            textangle=0,
            hovertemplate="<b>%{y}</b><br>%{customdata[1]}<br>Severity: %{customdata[0]}<br>Count: %{x}<extra></extra>"
        )
        
        # Update legend title
        fig.update_layout(legend_title_text="Priority")
    else:
        # Fallback: simple aggregation without severity
        stage_stats = df.groupby(["stage", "stage_order"]).size().reset_index(name="count")
        stage_stats = stage_stats.sort_values("stage_order")

        if stage_stats.empty:
            st.info("No stage data.")
            return None

        # Sorted stages for fallback
        stage_order_df = df[["stage", "stage_order"]].drop_duplicates().sort_values("stage_order")
        sorted_stages = stage_order_df["stage"].tolist()

        fig = px.bar(
            stage_stats,
            x="count",
            y="stage",
            orientation="h",
            text="count",
            title="",
            category_orders={"stage": sorted_stages},
        )
        fig.update_traces(marker_color=COLORS["primary"], textposition="auto")

    # Add Total Labels (Scatter Trace)
    # Filter stage_totals to only include stages present in sorted_stages (to avoid mismatch)
    stage_totals = stage_totals[stage_totals["stage"].isin(sorted_stages)]

    fig.add_trace(go.Scatter(
        x=stage_totals["total_count"],
        y=stage_totals["stage"],
        mode="text",
        text=stage_totals["total_count"].apply(lambda x: f"({x})"),
        textposition="middle right",
        hoverinfo="skip",
        showlegend=False,
        textfont=dict(color="white" if st.get_option("theme.base") == "dark" else "black"),
    ))

    # Calculate max range to fit the text label
    max_count = stage_totals["total_count"].max() if not stage_totals.empty else 0

    fig.update_layout(
        height=400,
        margin=dict(l=0, r=20, t=0, b=0), # Add right margin for labels
        font=dict(family="Inter, sans-serif"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        # yaxis=dict(autorange="reversed"),  # Removed reversal as requested
        xaxis=dict(
            showgrid=True,
            gridcolor="rgba(100,116,139,0.2)",
            range=[0, max_count * 1.15] # Extend range to fit labels
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title=None),
        barmode="stack",
    )

    return st.plotly_chart(
        fig,
        width="stretch",
        on_select="rerun",
        selection_mode=["points"]
    )




def _render_aging_chart(df: pd.DataFrame) -> dict | None:
    """Render boxplot of days in stage.

    Returns:
        Selection state dictionary or None
    """
    st.subheader("⏳ Stage Stickiness (Aging)")

    # Filter out completed/closed items to focus on active work aging
    # "Stickiness" implies items currently stuck in the flow.
    df = df[
        (df["stage_type"] != "completed") &
        (df["state"] != "closed")
    ].copy()

    # Sort stages by order for x-axis
    df_sorted = df.sort_values("stage_order")

    if df_sorted.empty:
        st.info("No data.")
        return None

    # Get sorted stages *after* filtering (Backlog might match but Done won't)
    # Actually, we should use the global order if possible, but filtered set is fine.
    # Note: df_sorted is already sorted by stage_order.
    # We can extract the unique list preserving order.
    # df_sorted["stage"].unique() returns in appearance order (which is sorted by stage_order)
    sorted_stages_aging = df_sorted["stage"].unique().tolist()

    fig = px.box(
        df_sorted,
        x="stage",
        y="days_in_stage",
        color="stage_type",
        color_discrete_map={
            "active": COLORS["active"],
            "waiting": COLORS["waiting"],
            "completed": COLORS["completed"],
            "active": COLORS["active"], # Duplicate key? No, just ensuring
        },
        category_orders={"stage": sorted_stages_aging}, # Force correct order
        points="outliers", # Show outliers
    )

    fig.update_layout(
        height=400,
        margin=dict(l=0, r=0, t=0, b=0),
        font=dict(family="Inter, sans-serif"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(showgrid=True, gridcolor="rgba(100,116,139,0.2)", title="Days in Stage"),
        xaxis=dict(title=None),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    return st.plotly_chart(
        fig,
        width="stretch",
        on_select="rerun",
        selection_mode=["points"]
    )


def _render_issue_detail_grid(df: pd.DataFrame) -> None:
    """Render unified issue detail grid with drill-down filters."""
    st.subheader("📋 Issue Drill-down")
    st.caption("Inspect issues by stage.")

    # 1. Multi-select Filter
    available_stages = sorted(df["stage"].unique(), key=lambda s: df[df["stage"] == s]["stage_order"].min())
    selected_stages = st.multiselect(
        "Filter by Stage",
        options=available_stages,
        default=[],
        help="Select stages to drill down into specifics."
    )

    # 2. Filter Data
    if selected_stages:
        display_df = df[df["stage"].isin(selected_stages)].copy()
    else:
        display_df = df.copy()

    # 3. Sort by Hierarchy (Parent -> Child) or Staleness
    # User requested hierarchical view.
    if "parent_id" in display_df.columns:
        # parent_id contains IID, so we must map to 'iid' column, not 'id'
        display_df = sort_hierarchy(display_df, parent_col="parent_id", id_col="iid", title_col="title")
    else:
        display_df = display_df.sort_values("days_in_stage", ascending=False)

    # 4. Select Columns
    cols_to_show = [
        "web_url", "title", "stage", "days_in_stage", "severity", "context", "milestone", "assignee"
    ]
    # Filter columns that exist
    cols = [c for c in cols_to_show if c in display_df.columns]

    # 5. Configure Columns and Render
    display_df = display_df[cols]
    
    # Reset index to ensure uniqueness for styling (sort_hierarchy can cause duplicate indices with exploded contexts)
    display_df = display_df.reset_index(drop=True)

    column_config = {
        "web_url": st.column_config.LinkColumn(
            "IID",
            display_text=r"/(?:issues|work_items)/(\d+)$",
            width="small",
            help="Click to open in GitLab"
        ),
        "assignee": st.column_config.TextColumn("Assignee", width="small"),
        "stage": st.column_config.TextColumn("Stage", width="small"),
        "title": st.column_config.TextColumn("Title", width="large"),
        "days_in_stage": st.column_config.NumberColumn(
            "Days in Stage",
            help="Days since last update in this stage",
            format="%d days",
        ),
        "severity": st.column_config.TextColumn("Priority", width="small"),
        "context": st.column_config.TextColumn("Context", width="small"),
        "milestone": st.column_config.TextColumn("Milestone", width="medium"),
    }

    # Apply styling if Context column exists
    styler = None
    if "context" in display_df.columns:
        from app.dashboard.data_loader import load_labels
        label_styles = load_labels()

        def highlight_context(val):
            if not isinstance(val, str):
                return None
            style = label_styles.get(val)
            if style:
                bg_color = style.get("color", "#FFFFFF")
                text_color = style.get("text_color", "#000000")
                return f'background-color: {bg_color}; color: {text_color}'
            return None

        styler = display_df.style.map(highlight_context, subset=["context"])

    column_order = ["web_url", "title", "stage", "days_in_stage", "severity", "milestone", "assignee"]
    if "context" in display_df.columns:
        column_order.insert(5, "context")

    # --- UI LAYOUT SELECTION ---
    col_layout, col_space = st.columns([1, 4])
    with col_layout:
        view_mode = st.radio(
            "View Mode", 
            ["Tabs", "Split"], 
            horizontal=True, 
            label_visibility="collapsed",
            help="Switch between Tabbed view and Split view"
        )
    
    # Define containers based on mode
    if view_mode == "Tabs":
        tab1, tab2 = st.tabs(["📋 Issue Drill-down", "🤖 AI Assistant"])
    else:
        tab1, tab2 = st.columns([1.5, 1], gap="medium")

    with tab1:
        st.caption("Select an issue to view AI insights.")
        
        # 1. Render Table with Selection
        selection = st.dataframe(
            styler if styler is not None else display_df,
            column_config=column_config,
            column_order=column_order,
            width="stretch",
            height=800,                   # Increased height for better visibility
            hide_index=True,
            on_select="rerun",           # Enable selection events
            selection_mode="single-row"  # Allow single row selection
        )

    # 2. Handle Selection & AI Tab
    with tab2:
        # Streamlit dataframe selection returns a dict-like object.
        # We should access "rows" safely.
        selection_state = selection.selection if hasattr(selection, "selection") else selection
        
        selected_indices = getattr(selection_state, "rows", [])
        if not selected_indices and isinstance(selection_state, dict):
             selected_indices = selection_state.get("rows", [])

        if not selected_indices:
            st.info("👈 Please select an issue from the 'Issue Drill-down' tab to start.")
        else:
            try:
                from app.ai.service import AIService
                
                # Get endpoint from sidebar settings
                ollama_endpoint = st.session_state.get("ollama_endpoint", "http://localhost:11434")
                ai_service = AIService(endpoint=ollama_endpoint)
                
                # Verify Ollama Connection first
                if not ai_service.check_health():
                    st.error(f"🔴 Ollama is offline at {ollama_endpoint}. Check AI Settings in sidebar.")
                    st.code("ollama serve", language="bash")
                else:
                    selected_idx = selected_indices[0]
                    selected_display_row = display_df.iloc[selected_idx]
                    
                    match_row = df[
                        (df["title"] == selected_display_row["title"]) & 
                        (df["web_url"] == selected_display_row["web_url"])
                    ].iloc[0]
                    
                    issue_id = int(match_row["id"])
                    
                    # Layout: Model Selector, Status, and Actions in a single header row
                    col_model, col_status, col_actions = st.columns([2, 2, 1])
                    
                    with col_model:
                        available_models = ai_service.get_available_models()
                        if not available_models:
                            st.warning("⚠️ No models found.")
                            selected_model = None
                        else:
                            selected_model = st.selectbox("Model", available_models, index=0)

                    if selected_model:
                        # Load AI Data
                        conversation = ai_service.get_conversation(issue_id)

                        # Check logic
                        is_stale = False
                        if conversation:
                            issue_updated = pd.to_datetime(match_row["updated_at"], utc=True)
                            if conversation.ref_issue_updated_at.tzinfo is None:
                                ref_updated = conversation.ref_issue_updated_at.replace(tzinfo=issue_updated.tzinfo)
                            else:
                                ref_updated = conversation.ref_issue_updated_at
                            
                            if issue_updated > ref_updated:
                                is_stale = True

                        with col_status:
                            st.write("")  # Spacer to align with selectbox
                            if is_stale:
                                st.warning("⚠️ Content changed")
                            elif conversation:
                                st.success("✅ Up to date")
                            else:
                                st.info("No summary yet")

                        with col_actions:
                            st.write("")  # Spacer to align with selectbox
                            if not conversation:
                                if st.button("✨ Generate", type="primary", use_container_width=True):
                                    with st.spinner(f"Generating..."):
                                        ai_service.generate_summary(match_row, model=selected_model)
                                        st.rerun()
                            else:
                                if st.button("🔄 Regenerate", use_container_width=True, help="Regenerate summary"):
                                    with st.spinner(f"Regenerating..."):
                                        ai_service.generate_summary(match_row, model=selected_model)
                                        st.rerun()

                        # Content Display
                        if conversation:
                            # Issue Metadata
                            issue_iid = match_row.get("iid", "N/A")
                            issue_title = match_row.get("title", "Unknown")
                            issue_labels = match_row.get("labels", [])
                            created_at = pd.to_datetime(match_row.get("created_at"), utc=True)
                            updated_at = pd.to_datetime(match_row.get("updated_at"), utc=True)

                            st.subheader(f"#{issue_iid} - {issue_title}")
                            
                            # Format labels as badges (handle list, array, or string)
                            if issue_labels is None:
                                labels_str = "_No labels_"
                            elif isinstance(issue_labels, (list, tuple)):
                                labels_str = " ".join([f"`{lbl}`" for lbl in issue_labels]) if len(issue_labels) > 0 else "_No labels_"
                            elif hasattr(issue_labels, '__iter__') and not isinstance(issue_labels, str):
                                # Handle numpy arrays or similar iterables
                                labels_list = list(issue_labels)
                                labels_str = " ".join([f"`{lbl}`" for lbl in labels_list]) if len(labels_list) > 0 else "_No labels_"
                            else:
                                labels_str = f"`{issue_labels}`" if issue_labels else "_No labels_"
                            
                            st.markdown(f"""
**Labels:** {labels_str}  
**Created:** {created_at.strftime('%Y-%m-%d %H:%M')} | **Updated:** {updated_at.strftime('%Y-%m-%d %H:%M')}
""")
                            st.divider()
                            st.markdown(conversation.summary_short)
                            
                            st.divider()
                            st.subheader("Chat Assistant")
                            
                            # Chat container
                            chat_container = st.container(height=400)
                            
                            # Display History
                            with chat_container:
                                for msg in conversation.chat_history:
                                    role_icon = "🤖" if msg.role == "assistant" else "👤"
                                    # Use Streamlit chat message
                                    with st.chat_message(msg.role):
                                        st.markdown(msg.content)

                            # Input (outside container to stick to bottom)
                            if prompt := st.chat_input("Ask about this issue..."):
                                with chat_container:
                                    with st.chat_message("user"):
                                        st.markdown(prompt)
                                
                                with st.status("Thinking...", expanded=True) as status:
                                    response = ai_service.chat(prompt, context=conversation, model=selected_model)
                                    status.update(label="Response generated!", state="complete", expanded=False)
                                
                                st.rerun()

            except Exception as e:
                st.error(f"Error loading AI Assistant: {e}")


