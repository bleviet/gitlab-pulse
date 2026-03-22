"""Tests for AI service prompt construction."""

from pathlib import Path

import pandas as pd

from app.ai.service import AIService, _build_summary_prompt


def test_build_summary_prompt_includes_notes_in_chronological_order() -> None:
    """The summary prompt should include the full issue discussion in time order."""
    issue_row = pd.Series(
        {
            "title": "Checkout error on retry",
            "description": "Customers report a 500 error during checkout retries.",
            "labels": ["type::bug", "priority::1"],
            "assignee": "alex",
            "milestone": "24.4",
            "state": "opened",
            "created_at": "2024-01-01T10:00:00Z",
            "updated_at": "2024-01-03T12:00:00Z",
            "notes": [
                {
                    "author_name": "Taylor",
                    "body": "Latest update: backend fix is deployed and QA is validating.",
                    "created_at": "2024-01-03T12:00:00Z",
                    "system": False,
                },
                {
                    "author_name": "GitLab",
                    "body": "changed milestone to 24.4",
                    "created_at": "2024-01-02T08:00:00Z",
                    "system": True,
                },
                {
                    "author_name": "Jordan",
                    "body": "Initial triage confirms the retry path is failing in payments.",
                    "created_at": "2024-01-01T11:00:00Z",
                    "system": False,
                },
            ],
        }
    )

    prompt = _build_summary_prompt(issue_row)

    assert "Summary: 2 to 4 sentences" in prompt
    assert "Key points: 3 to 6 bullet points" in prompt
    assert "Prefer the most recent confirmed information when comments conflict." in prompt
    assert "System note by GitLab: changed milestone to 24.4" in prompt
    assert "Comment by Jordan: Initial triage confirms the retry path is failing in payments." in prompt
    assert "Comment by Taylor: Latest update: backend fix is deployed and QA is validating." in prompt
    assert prompt.index("Initial triage confirms the retry path is failing in payments.") < prompt.index(
        "changed milestone to 24.4"
    ) < prompt.index("Latest update: backend fix is deployed and QA is validating.")


def test_generate_summary_uses_full_issue_prompt(tmp_path: Path, monkeypatch) -> None:
    """generate_summary should pass the full issue content prompt to Ollama."""
    service = AIService(storage_path=str(tmp_path))
    issue_row = pd.Series(
        {
            "id": 7,
            "project_id": 101,
            "title": "Improve export job resiliency",
            "description": "Retry the export worker after transient S3 errors.",
            "labels": ["type::feature"],
            "assignee": "sam",
            "milestone": "Backlog",
            "state": "opened",
            "created_at": "2024-02-01T08:00:00Z",
            "updated_at": "2024-02-03T09:30:00Z",
            "notes": [
                {
                    "author_name": "Morgan",
                    "body": "Decision: add exponential backoff and requeue failed exports.",
                    "created_at": "2024-02-02T10:00:00Z",
                    "system": False,
                }
            ],
        }
    )

    captured: dict[str, str] = {}

    def fake_call_generate(model: str, prompt: str, stream: bool = False) -> str:
        captured["model"] = model
        captured["prompt"] = prompt
        captured["stream"] = str(stream)
        return "Generated summary"

    monkeypatch.setattr(service, "_call_generate", fake_call_generate)

    conversation = service.generate_summary(issue_row, model="llama3:test")

    assert conversation.summary_short == "Generated summary"
    assert captured["model"] == "llama3:test"
    assert captured["stream"] == "False"
    assert "Here is the full issue content:" in captured["prompt"]
    assert "Decision: add exponential backoff and requeue failed exports." in captured["prompt"]
    assert "Do not invent facts or fill gaps with assumptions." in captured["prompt"]
