"""AI Assistant Widget."""

import pandas as pd
import streamlit as st
try:
    from app.ai.service import AIService
except ImportError:
    AIService = None


def ai_assistant(df: pd.DataFrame, display_df: pd.DataFrame) -> None:
    """Render the AI Assistant panel for issue insights.

    Args:
        df: Full DataFrame of issues (for finding matches by columns not in display)
        display_df: Currently displayed DataFrame (for mapping selection indices)
    """
    # We need to access the selection from the table.
    # Since the table might be in another column or not rendered in the same run (if tabs switched),
    # we rely on st.session_state for the 'issue_drilldown_table' key (or generic key).
    
    # In overview.py this is "issue_drilldown_table" (from legacy helper). 
    # But usually widgets should be configured with a key.
    # For now, we assume standard key or session state presence.

    selection_state = st.session_state.get("issue_drilldown_table", {})

    # Handle Snowpark/Streamlit selection object structure
    if hasattr(selection_state, "selection"):
        selection_state = selection_state.selection

    selected_indices = getattr(selection_state, "rows", [])
    # Access dict if it's a dict
    if not selected_indices and isinstance(selection_state, dict):
        selected_indices = selection_state.get("rows", [])

    # Try to find the matching row - either from current selection or persisted state
    match_row = None

    if selected_indices:
        # Use current selection
        selected_idx = selected_indices[0]
        if selected_idx < len(display_df):
            selected_display_row = display_df.iloc[selected_idx]
            # Match by unique identifier (web_url is usually good)
            matches = df[df["web_url"] == selected_display_row["web_url"]]
            if not matches.empty:
                match_row = matches.iloc[0]
    else:
        # Fall back to persisted selection (survives sorting/rerun)
        persisted_url = st.session_state.get("selected_issue_url", "")
        if persisted_url:
            matches = df[df["web_url"] == persisted_url]
            if not matches.empty:
                match_row = matches.iloc[0]

    if match_row is None:
        st.info("👈 Please select an issue from the table to start.")
        return

    if AIService is None:
        st.error("AI Service not available (imports failed).")
        return

    try:
        # Get endpoint from sidebar settings
        ollama_endpoint = st.session_state.get("ollama_endpoint", "http://localhost:11434")
        ai_service = AIService(endpoint=ollama_endpoint)

        # Verify Ollama Connection first
        if not ai_service.check_health():
            st.error(f"🔴 Ollama is offline at {ollama_endpoint}. Check AI Settings in sidebar.")
            st.code("ollama serve", language="bash")
        else:
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
                    _render_ai_content(match_row, conversation, ai_service, selected_model)

    except Exception as e:
        st.error(f"Error loading AI Assistant: {e}")


def _render_ai_content(match_row, conversation, ai_service, selected_model):
    """Render the summary and chat interface."""
    # Issue Metadata
    issue_iid = match_row.get("iid", "N/A")
    issue_title = match_row.get("title", "Unknown")
    issue_labels = match_row.get("labels", [])
    created_at = pd.to_datetime(match_row.get("created_at"), utc=True)
    updated_at = pd.to_datetime(match_row.get("updated_at"), utc=True)

    st.subheader(f"#{issue_iid} - {issue_title}")
    
    # Format labels as badges
    if issue_labels is None:
        labels_str = "_No labels_"
    elif isinstance(issue_labels, (list, tuple)):
        labels_str = " ".join([f"`{lbl}`" for lbl in issue_labels]) if len(issue_labels) > 0 else "_No labels_"
    elif hasattr(issue_labels, '__iter__') and not isinstance(issue_labels, str):
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
