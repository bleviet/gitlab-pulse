# GitLabInsight

A versatile analytics platform for GitLab issue data. Extracts, validates, and visualizes workflow health and throughput using a **Clean Architecture** and **Medallion Data Pattern**.

## Quick Start

```bash
# Install dependencies
uv sync --dev


# Generate synthetic test data (Local)
uv run python tools/seeder.py --count 1000 --inject-errors

# Or manage local synthetic projects interactively
uv run python tools/local_data_manager.py

# Or seed a live GitLab project (Remote)
uv run python tools/gitlab_seeder.py --project-id <YOUR_PROJECT_ID> --count 50 --inject-errors

# Process data (Layer 2)
uv run python app/processor/main.py

# Launch dashboard
uv run streamlit run app/dashboard/main.py
```

## Architecture

| Layer | Component | Description |
|-------|-----------|-------------|
| **L0** | `data/raw/` | Raw JSON from GitLab API |
| **L1** | `app/collector/` | Hybrid REST+GraphQL collector |
| **L2** | `app/processor/` | Domain logic & validation |
| **L3** | `app/dashboard/` | Hierarchical Streamlit visualization |

## Configuration

### Environment Variables

```bash
export GITLAB_URL="https://gitlab.com"
export GITLAB_TOKEN="your-token"
export PROJECT_IDS="12345,67890"
```

`tools/seeder.py` generates synthetic local Parquet files directly in `data/processed/` and does not create live GitLab projects. Keep `PROJECT_IDS` limited to real GitLab project IDs when running `app/collector/orchestrator.py`.

### Reset and Recreate Local Seeded Data

If you want to discard the synthetic local dataset and generate a fresh one with more realistic totals, delete the seeded outputs and run the seeder again:

```bash
# Remove seeded Layer 1 files
rm -f data/processed/issues_101.parquet data/processed/issues_102.parquet data/processed/issues_103.parquet

# Optionally clear Layer 2 analytics output
rm -f data/analytics/*.parquet

# Optionally reset collector sync state
rm -f data/state/sync_state.json

# Recreate local seeded data with more volume
uv run python tools/seeder.py --count 5000 --projects 101,102,103 --inject-errors --seed 42

# Rebuild analytics
uv run python app/processor/main.py
```

Increasing `--count` gives you more total tickets. By default, the seeder assigns an assignee to roughly 95% of generated issues, and you can override that with `--assignment-rate`.

Synthetic issues now use local dashboard URLs by default, so clicking issue links during local testing stays inside your local environment instead of pointing at a fake GitLab host.

### Local Data Manager

For faster testing and validation, use the terminal manager:

```bash
uv run python tools/local_data_manager.py
```

It can:
- detect local projects from `data/processed/issues_*.parquet`
- show per-project counts, open/closed totals, assigned totals, and unique assignees
- create or reseed local projects with different options
- delete selected local projects or all detected local data
- rebuild analytics after changes
- reset, reseed, and rebuild in one flow

You can also use it non-interactively:

```bash
# List detected local projects
uv run python tools/local_data_manager.py --action list

# Create or reseed specific projects
uv run python tools/local_data_manager.py \
  --action seed \
  --project-ids 101,102,103 \
  --count 5000 \
  --assignment-rate 1.0 \
  --max-team-members 8 \
  --dashboard-url-base http://localhost:8501 \
  --seed 42

# Delete specific local projects
uv run python tools/local_data_manager.py --action delete --project-ids 101,102,103
```

The seeder now supports:
- `--assignment-rate` to control how many issues get an assignee
- `--max-team-members` to cap the number of distinct assignees and simulate a realistic team size
- `--dashboard-url-base` to control where synthetic issue links should open

When you open a seeded issue from the dashboard, the overview details dialog now renders the issue from local parquet data instead of calling the GitLab API. This makes local feature testing possible even when the issue URL points back to your local dashboard.

If your dashboard runs on a different host or port, regenerate the data with a matching base URL:

```bash
uv run python tools/seeder.py \
  --count 5000 \
  --projects 101,102,103 \
  --dashboard-url-base http://192.168.1.50:8501
```

### Rules Configuration

Edit `app/config/rules/default.yaml` to customize:
- **Classification Rules**: Define Type, Severity, and Priority using flexible matching:
  ```yaml
  classification:
    type:
      Bug:
        labels: ["type::bug"]
        title: ["contains:fix", "contains:crash"]
  ```
- **Validation**: Enforce required labels (e.g., Bugs must have Severity).
- **Contexts & Workflows**: Slice data by domain and define process stages.

## AI Assistant (Layer 4)

GitLabInsight includes a **local AI assistant** powered by [Ollama](https://ollama.com/). This enables context-aware issue summarization and chat without sending data to external APIs.

### Setup

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model
ollama pull llama3

# Start the server (if not already running)
ollama serve
```

### Features

- **Executive Summary:** Generates a structured summary (Technical Details, Status, Next Steps) for any issue.
- **Chat Interface:** Ask follow-up questions with full issue context.
- **Staleness Detection:** Automatically flags when an issue has changed since the last summary.
- **Multi-Server Support:** Configure remote Ollama servers via the sidebar (Settings > 🤖 AI Settings).
- **Persistence:** Summaries and chat history are saved to `data/ai/` for future sessions.

### Usage

1. Go to the **Flow** tab in the dashboard.
2. Select an issue from the **Issue Drill-down** table.
3. Switch to the **🤖 AI Assistant** tab.
4. Click **✨ Generate** to create a summary, or **🔄 Regenerate** to update it.

## Testing

```bash
# Run unit tests
uv run pytest tests/ -v

# Generate test data with errors
uv run python tools/seeder.py --count 10000 --inject-errors

# Generate test data with a bounded team size
uv run python tools/seeder.py --count 10000 --assignment-rate 1.0 --max-team-members 8

# Profile Layer 2 performance
uv run python -m cProfile -s time app/processor/main.py
```

## Q&A

### Data Inclusion Logic
**Q: Are quality issues included in "Open Issues" or "Bug Ratio" metrics?**
**A:** No. The operational metrics shown in the Overview page are calculated exclusively from the **valid** dataset. Issues that fail validation (e.g., missing labels) are stripped out and do not affect those metrics.

**Q: Do the issue lists include quality issues?**
**A:** No. The list in the Overview view shows only valid issues. Invalid issues are displayed **exclusively** in the **Hygiene** view's Action Table.

**Q: What are "Backlog" items?**
**A:** "Backlog" is the default classification for any valid issue that **does not match** any specific workflow stage defined in `rules.yaml`. These issues are considered `waiting` (Inventory) and have not yet entered the active development process.

### Multi-Context Issues
**Q: What if an issue belongs to multiple contexts (e.g., "R&D" and "Customer")?**
**A:**
- **Metrics & Charts**: The issue is counted **only once** (deduplicated).
- **Issue Table**: The issue appears **twice** (or more), once for each context, allowing you to see it in every relevant slice.

### Help & Descriptions
**Q: Where can I find stage definitions?**
**A:** Hover over the bars in the **Work by Stage** chart. The tooltips now display a detailed description of each stage (e.g., "Code review and merge request feedback") as configured in your `default.yaml`. A general help icon `(?)` in the chart header also provides usage instructions.

## License

MIT
