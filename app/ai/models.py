from datetime import datetime
from typing import List

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A single message in the chat history."""

    role: str = Field(..., description="Role of the sender: 'user', 'assistant', or 'system'")
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class IssueConversation(BaseModel):
    """Persistent storage for issue-related AI interactions."""

    issue_id: int
    project_id: int

    # Staleness Logic
    ref_issue_updated_at: datetime  # The updated_at of the issue when this summary was generated
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    # Content
    summary_short: str
    chat_history: List[ChatMessage] = Field(default_factory=list)
