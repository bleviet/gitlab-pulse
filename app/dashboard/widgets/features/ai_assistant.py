"""AI Assistant Widget."""

from collections.abc import Iterable

import pandas as pd
import requests
import streamlit as st

from app.ai.models import IssueConversation

try:
    from app.ai.service import AIService
except ImportError:
    AIService = None


def _conversation_is_stale(
    issue_row: pd.Series,
    conversation: IssueConversation,
) -> bool:
    """Return whether the issue changed since the persisted summary was generated."""
    issue_updated = pd.to_datetime(issue_row.get("updated_at"), utc=True, errors="coerce")
    if pd.isna(issue_updated):
        return False

    ref_updated = pd.Timestamp(conversation.ref_issue_updated_at)
    if ref_updated.tzinfo is None:
        ref_updated = ref_updated.tz_localize("UTC")
    else:
        ref_updated = ref_updated.tz_convert("UTC")

    return issue_updated > ref_updated


def _format_issue_labels(issue_labels: object) -> str:
    """Render issue labels as inline code spans for the assistant header."""
    if issue_labels is None:
        return "_No labels_"

    if isinstance(issue_labels, str):
        labels = [issue_labels] if issue_labels.strip() else []
    elif isinstance(issue_labels, Iterable):
        labels = [str(label).strip() for label in issue_labels if str(label).strip()]
    else:
        labels = [str(issue_labels).strip()] if str(issue_labels).strip() else []

    return " ".join(f"`{label}`" for label in labels) if labels else "_No labels_"


def _format_issue_timestamp(value: object) -> str:
    """Format a timestamp for AI issue context metadata."""
    parsed = pd.to_datetime(value, utc=True, errors="coerce")
    if pd.isna(parsed):
        return "Unknown"
    return parsed.strftime("%Y-%m-%d %H:%M UTC")


def ai_assistant(issue_row: pd.Series, *, widget_key_prefix: str = "issue-dialog-ai") -> None:
    """Render the AI Assistant panel for one selected issue."""
    if AIService is None:
        st.error("AI Service not available (imports failed).")
        return

    try:
        issue_id = int(issue_row["id"])
    except (KeyError, TypeError, ValueError):
        st.error("This issue is missing the metadata required for AI features.")
        return

    ollama_endpoint = st.session_state.get("ollama_endpoint", "http://localhost:11434")
    ai_service = AIService(endpoint=ollama_endpoint)

    if not ai_service.check_health():
        st.error(f"🔴 Ollama is offline at {ollama_endpoint}. Check AI Settings in sidebar.")
        st.code("ollama serve", language="bash")
        return

    available_models = ai_service.get_available_models()
    if not available_models:
        st.warning("⚠️ No models found.")
        return

    model_state_key = f"{widget_key_prefix}-model"
    persisted_model = st.session_state.get(model_state_key)
    default_index = 0
    if isinstance(persisted_model, str) and persisted_model in available_models:
        default_index = available_models.index(persisted_model)

    conversation = ai_service.get_conversation(issue_id)
    is_stale = conversation is not None and _conversation_is_stale(issue_row, conversation)

    col_model, col_status, col_actions = st.columns([2, 2, 1], gap="small")

    with col_model:
        selected_model = st.selectbox(
            "Model",
            available_models,
            index=default_index,
            key=model_state_key,
        )

    with col_status:
        st.write("")
        if is_stale:
            st.warning("⚠️ Content changed")
        elif conversation is not None:
            st.success("✅ Up to date")
        else:
            st.info("No summary yet")

    with col_actions:
        st.write("")
        action_key = f"{widget_key_prefix}-generate"
        action_label = "✨ Generate"
        action_help: str | None = None
        if conversation is not None:
            action_key = f"{widget_key_prefix}-regenerate"
            action_label = "🔄 Regenerate"
            action_help = "Regenerate summary"

        if st.button(
            action_label,
            key=action_key,
            type="primary" if conversation is None else "secondary",
            help=action_help,
            use_container_width=True,
        ):
            try:
                with st.spinner("Generating summary..." if conversation is None else "Regenerating summary..."):
                    ai_service.generate_summary(issue_row, model=selected_model)
            except requests.RequestException as exc:
                st.error(f"Failed to generate AI summary: {exc}")
            else:
                st.rerun()

    if conversation is not None:
        _render_ai_content(
            issue_row,
            conversation,
            ai_service,
            selected_model,
            widget_key_prefix=widget_key_prefix,
        )


def _render_ai_content(
    issue_row: pd.Series,
    conversation: IssueConversation,
    ai_service: "AIService",
    selected_model: str,
    *,
    widget_key_prefix: str,
) -> None:
    """Render the summary and chat interface."""
    issue_iid = issue_row.get("iid", "N/A")
    issue_title = issue_row.get("title", "Unknown")

    st.subheader(f"#{issue_iid} - {issue_title}")
    st.markdown(
        f"**Labels:** {_format_issue_labels(issue_row.get('labels'))}  \n"
        f"**Created:** {_format_issue_timestamp(issue_row.get('created_at'))} | "
        f"**Updated:** {_format_issue_timestamp(issue_row.get('updated_at'))}"
    )
    st.divider()
    st.markdown(conversation.summary_short)

    st.divider()
    st.subheader("Chat Assistant")
    chat_container = st.container(height=400)

    with chat_container:
        for message in conversation.chat_history:
            with st.chat_message(message.role):
                st.markdown(message.content)

    prompt = st.chat_input(
        "Ask about this issue...",
        key=f"{widget_key_prefix}-chat-input",
    )
    if prompt:
        try:
            with st.status("Thinking...", expanded=True) as status:
                ai_service.chat(prompt, context=conversation, model=selected_model)
                status.update(label="Response generated!", state="complete", expanded=False)
        except requests.RequestException as exc:
            st.error(f"Failed to generate AI response: {exc}")
        else:
            st.rerun()
