import json
import logging
from pathlib import Path
from typing import List, Optional

import pandas as pd
import requests

from app.ai.models import ChatMessage, IssueConversation

logger = logging.getLogger(__name__)


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

    def get_available_models(self) -> List[str]:
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

    def get_conversation(self, issue_id: int) -> Optional[IssueConversation]:
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
        title = issue_row.get("title", "Unknown")
        description = issue_row.get("description", "No description provided.")
        labels = issue_row.get("labels", [])
        
        system_prompt = f"""
You are a technical assistant for a Firmware R&D team using GitLab.
Your goal is to help engineers quickly understand the state of a bug or feature.

Context:
- Issue Title: {title}
- Description: {description}
- Labels: {labels}

Instructions:
1. Provide a concise "Executive Summary" (2-5 sentences max).
2. List key "Technical Details" (logs, hex codes, register values observed).
3. Identify the "Current Status" and any blocking dependencies.
4. Suggest potential "Next Steps" based on standard firmware debugging workflows.

Output format: Markdown.
"""
        
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

    def _call_chat(self, model: str, messages: List[dict], stream: bool = False) -> str:
        """Raw call to /api/chat."""
        try:
            payload = {"model": model, "messages": messages, "stream": stream}
            response = requests.post(f"{self.endpoint}/api/chat", json=payload, timeout=60.0)
            response.raise_for_status()
            return response.json().get("message", {}).get("content", "")
        except requests.RequestException as e:
            logger.error(f"Ollama Chat Error: {e}")
            raise
