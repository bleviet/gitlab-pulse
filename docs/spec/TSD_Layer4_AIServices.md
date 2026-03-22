# Technical Specification: Layer 4 - AI Services

**Status:** Implemented  
**Version:** 1.1

## 1. Concept

GitLabInsight treats AI summaries and issue chats as persistent local artifacts rather than temporary UI state. Each issue can accumulate a saved summary and chat history under `data/ai/`.

## 2. Implemented Workflow

1. User selects an issue from the Overview drill-down flow.
2. The dashboard looks for `data/ai/chat_{issue_id}.parquet`.
3. If no conversation exists, the UI offers **Generate**.
4. If a conversation exists, the UI compares the current issue `updated_at` with `ref_issue_updated_at`.
5. If the issue changed since the last summary, the UI marks the content as stale and offers **Regenerate**.
6. The user can continue chatting against the persisted summary context.

## 3. Implemented Components

### 3.1 Storage models

`app/ai/models.py` defines:

- `ChatMessage`
- `IssueConversation`

`IssueConversation.ref_issue_updated_at` is the timestamp anchor for staleness detection.

### 3.2 Service

`app/ai/service.py` currently provides:

- `check_health()`
- `get_available_models()`
- `get_conversation(issue_id)`
- `save_conversation(conversation)`
- `generate_summary(issue_row, model=...)`
- `chat(user_prompt, context, model=...)`

### 3.3 Dashboard integration

The current UI integration lives in:

- `app/dashboard/widgets/features/ai_assistant.py`
- `app/dashboard/views/overview.py`
- `app/dashboard/sidebar.py`

The sidebar stores configurable Ollama endpoint choices in `data/state/ollama_servers.json`.

## 4. Persistence Model

| Path | Purpose |
| :---- | :---- |
| `data/ai/chat_{issue_id}.parquet` | Persisted summary and chat history for one issue |
| `data/state/ollama_servers.json` | Saved endpoint choices for the sidebar |

## 5. Current UI Behavior

- health-check the configured Ollama server before rendering AI actions
- fetch the installed model list from Ollama
- show `No summary yet`, `Up to date`, or `Content changed`
- allow generate or regenerate actions
- render persisted chat history
- append new user/assistant turns after each chat request

## 6. Current Limitations

- The feature depends on a reachable Ollama-compatible endpoint
- The default endpoint is local-first: `http://localhost:11434`
- AI is currently surfaced through the Overview issue drill-down flow rather than as a standalone top-level page

## 7. Rationale

- **Privacy:** local-first execution keeps issue context on your infrastructure by default
- **Persistence:** saved summaries become reusable project context
- **Staleness by timestamp:** comparing `updated_at` to `ref_issue_updated_at` is simple and cheap
