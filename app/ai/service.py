import logging
from pathlib import Path
from typing import TypedDict

import pandas as pd
import requests

from app.ai.models import ChatMessage, IssueConversation

logger = logging.getLogger(__name__)


class _PromptNote(TypedDict):
    """Normalized note data used to build the summary prompt."""

    author: str
    body: str
    created_at: str
    system: bool


def _format_prompt_field(value: object, fallback: str) -> str:
    """Return a normalized prompt field value."""
    if value is None:
        return fallback
    text = str(value).strip()
    return text if text else fallback


def _format_prompt_labels(labels: object) -> str:
    """Return labels as a concise comma-separated string for the prompt."""
    if labels is None:
        return "None"
    if isinstance(labels, str):
        normalized_labels = [labels.strip()] if labels.strip() else []
    elif hasattr(labels, "tolist"):
        normalized_labels = [
            str(label).strip()
            for label in labels.tolist()
            if str(label).strip()
        ]
    elif isinstance(labels, list | tuple | set):
        normalized_labels = [str(label).strip() for label in labels if str(label).strip()]
    else:
        normalized_labels = [str(labels).strip()] if str(labels).strip() else []
    return ", ".join(normalized_labels) if normalized_labels else "None"


def _normalize_notes_for_prompt(raw_notes: object) -> list[_PromptNote]:
    """Return prompt-ready note entries sorted in chronological order."""
    if raw_notes is None:
        return []

    values = raw_notes.tolist() if hasattr(raw_notes, "tolist") else raw_notes
    if isinstance(values, dict):
        values = [values]
    if not isinstance(values, list | tuple):
        return []

    normalized_notes: list[_PromptNote] = []
    for value in values:
        if not isinstance(value, dict):
            continue
        author = _format_prompt_field(
            value.get("author_name") or value.get("author_username"),
            "Unknown author",
        )
        normalized_notes.append(
            {
                "author": author,
                "body": _format_prompt_field(value.get("body"), "(empty note)"),
                "created_at": _format_prompt_field(value.get("created_at"), "Unknown time"),
                "system": bool(value.get("system", False)),
            }
        )

    return sorted(normalized_notes, key=_prompt_note_sort_key)


def _prompt_note_sort_key(note: _PromptNote) -> tuple[int, str]:
    """Build a stable sort key for prompt note ordering."""
    parsed = pd.to_datetime(note["created_at"], utc=True, errors="coerce")
    if pd.isna(parsed):
        return (1, note["created_at"])
    return (0, parsed.isoformat())


def _format_notes_for_prompt(raw_notes: object) -> str:
    """Render issue notes/comments for the summary prompt."""
    notes = _normalize_notes_for_prompt(raw_notes)
    if not notes:
        return "- No notes or comments provided."

    lines: list[str] = []
    for index, note in enumerate(notes, start=1):
        note_kind = "System note" if note["system"] else "Comment"
        lines.append(
            f"{index}. [{note['created_at']}] {note_kind} by {note['author']}: {note['body']}"
        )
    return "\n".join(lines)


def _build_summary_prompt(issue_row: pd.Series) -> str:
    """Build the issue-summary prompt from the full issue content."""
    title = _format_prompt_field(issue_row.get("title"), "Unknown")
    description = _format_prompt_field(
        issue_row.get("description"),
        "No description provided.",
    )
    labels = _format_prompt_labels(issue_row.get("labels"))
    assignee = _format_prompt_field(issue_row.get("assignee"), "Unassigned")
    milestone = _format_prompt_field(issue_row.get("milestone"), "None")
    state = _format_prompt_field(issue_row.get("state"), "unknown")
    created_at = _format_prompt_field(issue_row.get("created_at"), "Unknown")
    updated_at = _format_prompt_field(issue_row.get("updated_at"), "Unknown")
    notes = _format_notes_for_prompt(issue_row.get("notes"))

    return f"""Summarize the following GitLab issue in a neutral, concise, and factual way. Use the entire issue content, including the title, description, system notes if relevant, and all user comments/notes. Do not ignore later comments, because they may update or contradict earlier information.

Produce the output in this structure:

Summary: 2 to 4 sentences describing the issue, current state, and most important context.

Key points: 3 to 6 bullet points covering confirmed facts, decisions, blockers, status changes, and next steps.

Open questions: bullet points only if unresolved questions remain.

Requirements:

- Be neutral and concise.
- Do not invent facts or fill gaps with assumptions.
- Prefer the most recent confirmed information when comments conflict.
- Mention disagreements or uncertainty briefly if they affect the current status.
- Do not repeat the same point from multiple comments.
- Do not quote long passages.
- Do not include praise, blame, or subjective judgment.
- If the discussion is noisy, focus on decisions, actions, blockers, and current status.

Here is the full issue content:

Title: {title}

Description:
{description}

Metadata:
- Labels: {labels}
- Assignee: {assignee}
- Milestone: {milestone}
- State: {state}
- Created at: {created_at}
- Updated at: {updated_at}

Notes and comments in chronological order:
{notes}
"""


class AIService:
    """Service to interact with local Ollama instance and manage conversation state."""

    def __init__(self, endpoint: str = "http://localhost:11434", storage_path: str = "data/ai"):
        self.endpoint = endpoint.rstrip("/")
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def check_health(self) -> bool:
        """Check if Ollama service is running."""
        try:
            response = requests.get(f"{self.endpoint}/", timeout=1.0)
            return response.status_code == 200
        except requests.RequestException:
            return False

    def get_available_models(self) -> list[str]:
        """Fetch list of available models from Ollama."""
        try:
            response = requests.get(f"{self.endpoint}/api/tags", timeout=2.0)
            if response.status_code == 200:
                data = response.json()
                # Extract model names (e.g., 'llama3:latest')
                return [model["name"] for model in data.get("models", [])]
            return []
        except requests.RequestException as e:
            logger.error(f"Failed to fetch models: {e}")
            return []

    def get_conversation(self, issue_id: int) -> IssueConversation | None:
        """Load conversation for a specific issue from Parquet."""
        filepath = self.storage_path / f"chat_{issue_id}.parquet"
        if not filepath.exists():
            return None

        try:
            df = pd.read_parquet(filepath)
            if df.empty:
                return None

            # Reconstruct from single-row DataFrame
            data = df.iloc[0].to_dict()

            # Parse nested JSON structures if stored as strings (common for complex types in Parquet)
            # However, direct Pydantic dump -> Parquet usually handles lists naturally if using pyarrow
            # For robustness, we'll assume standard JSON serialization for complex fields if needed
            # But let's verify if we need bespoke logic.
            # Strategy: Store specific fields. For simplicity in V1, let's use the raw dict

            # Note: Parquet handles lists, but validation is safer
            return IssueConversation(**data)
        except Exception as e:
            logger.error(f"Failed to load conversation {issue_id}: {e}")
            return None

    def save_conversation(self, conversation: IssueConversation):
        """Save conversation state to Parquet."""
        filepath = self.storage_path / f"chat_{conversation.issue_id}.parquet"
        try:
            # Convert to dict and then DataFrame
            data = conversation.model_dump()
            df = pd.DataFrame([data])
            df.to_parquet(filepath)
        except Exception as e:
            logger.error(f"Failed to save conversation {conversation.issue_id}: {e}")

    def generate_summary(self, issue_row: pd.Series, model: str = "llama3:latest") -> IssueConversation:
        """Generate a summary for an issue row."""
        system_prompt = _build_summary_prompt(issue_row)


        # Call Generate API
        summary_text = self._call_generate(model, system_prompt, stream=False)

        # Create Conversation Object
        conversation = IssueConversation(
            issue_id=int(issue_row["id"]),
            project_id=int(issue_row["project_id"]),
            ref_issue_updated_at=pd.to_datetime(issue_row["updated_at"], utc=True),
            summary_short=summary_text
        )

        self.save_conversation(conversation)
        return conversation

    def chat(self, user_prompt: str, context: IssueConversation, model: str = "llama3:latest") -> str:
        """Continue conversation about the issue."""
        # Append User Message
        context.chat_history.append(ChatMessage(role="user", content=user_prompt))

        # Build Context for LLM
        # We include the summary as the "system" context for the chat
        messages = [
            {"role": "system", "content": f"Context Summary:\n{context.summary_short}"}
        ]

        for msg in context.chat_history:
             messages.append({"role": msg.role, "content": msg.content})

        # Call Chat API
        response_text = self._call_chat(model, messages, stream=False)

        # Append Assistant Response
        context.chat_history.append(ChatMessage(role="assistant", content=response_text))

        self.save_conversation(context)
        return response_text

    def _call_generate(self, model: str, prompt: str, stream: bool = False) -> str:
        """Raw call to /api/generate."""
        try:
            payload = {"model": model, "prompt": prompt, "stream": stream}
            response = requests.post(f"{self.endpoint}/api/generate", json=payload, timeout=60.0)
            response.raise_for_status()
            if stream:
                # Basic stream handling (not yet used in UI)
                return ""
            return response.json().get("response", "")
        except requests.RequestException as e:
            logger.error(f"Ollama Generate Error: {e}")
            raise

    def _call_chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        stream: bool = False,
    ) -> str:
        """Raw call to /api/chat."""
        try:
            payload = {"model": model, "messages": messages, "stream": stream}
            response = requests.post(f"{self.endpoint}/api/chat", json=payload, timeout=60.0)
            response.raise_for_status()
            return response.json().get("message", {}).get("content", "")
        except requests.RequestException as e:
            logger.error(f"Ollama Chat Error: {e}")
            raise
