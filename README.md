# GitLab Pulse

A versatile analytics platform for GitLab issue data. Extracts, validates, and visualizes workflow health and throughput using a **Clean Architecture** and **Medallion Data Pattern**.

## Requirements

- **Python**: `>=3.11`
- **Package Manager**: [`uv`](https://docs.astral.sh/uv/)
- **Platform**: Linux, macOS, or Windows (WSL recommended)
- **AI (Optional)**: [Ollama](https://ollama.com/) for local assistant features

## Quick Start

You can run GitLab Pulse either locally on your host or isolated within a Docker container. Both methods can auto-generate synthetic data for a zero-configuration demo.

### Option 1: Docker Evaluation (Recommended for Demos)

For an isolated evaluation environment without installing Python dependencies on your host, use Docker. 

```bash
# Copy environment template
cp .env.example .env

# Start the application using Docker Compose
docker compose up --build
```

**What happens?**
* The container builds and installs dependencies internally.
* If no data exists, the container automatically generates and processes synthetic test data internally.
* This generated data (and any AI chats) is saved to the `./data` directory on your host via volume mounting.
* Open `http://localhost:8501` to view your dashboard.

*Note: This Docker setup is intended as an optional onboarding/testing path, not as a replacement for the native workflow.*

### Option 2: Native Host Setup (Recommended for Development)

The fastest way to set up the native Python environment on your host is via the included `setup.sh` script:

```bash
./setup.sh
```

**What happens?**
* **Prerequisites Check**: Verifies Python and `uv` are installed.
* **Dependencies**: Runs `uv sync` to install all required packages on your host.
* **Configuration**: Copies `.env.example` to `.env` if it doesn't exist.
* **Local Data (Optional)**: Prompts you to generate and process synthetic data locally so you can use the dashboard immediately without a GitLab connection.
* **Result**: You are left with a fully configured local Python environment ready to run `uv run streamlit run app/dashboard/main.py`.

### Option 3: Manual Native Setup

If you prefer to run the steps manually instead of using `setup.sh`:

```bash
# Install dependencies
uv sync

# Copy environment template
cp .env.example .env
```

**For Synthetic Data (No GitLab Connection Needed):**
```bash
# Generate synthetic test data
uv run python tools/seeder.py --count 1000 --inject-errors

# Process the data
uv run python app/processor/main.py

# Launch dashboard
uv run streamlit run app/dashboard/main.py
```

**For Live GitLab Data:**
```bash
# 1. Edit .env and configure GITLAB_URL, GITLAB_TOKEN, and PROJECT_IDS

# 2. Fetch data from GitLab
uv run python app/collector/orchestrator.py

# 3. Process the fetched data
uv run python app/processor/main.py

# 4. Launch dashboard
uv run streamlit run app/dashboard/main.py
```

## Architecture

| Layer | Component | Description |
|-------|-----------|-------------|
| **L0** | `data/raw/` | Raw JSON from GitLab API |
| **L1** | `app/collector/` | Hybrid REST+GraphQL collector |
| **L2** | `app/processor/` | Domain logic & validation |
| **L3** | `app/dashboard/` | Hierarchical Streamlit visualization |

## Production Deployment

While GitLab Pulse can be run entirely on a laptop, deploying it for team use requires a few operational considerations:

### Minimal Deployment Steps
1. Clone the repository on a server.
2. `cp .env.example .env` and configure your `GITLAB_URL`, `GITLAB_TOKEN` (with `read_api`), and `PROJECT_IDS`.
3. Set a secure `ADMIN_PASSWORD` in `.env` for dashboard changes.
4. Schedule `uv run python app/collector/orchestrator.py` to run periodically (e.g., via cron) to ingest new data.
5. Schedule `uv run python app/processor/main.py` to run after the collector to update analytics.
6. Serve the dashboard as a long-running process: `uv run streamlit run app/dashboard/main.py`.

### Persistent Storage
If deploying via Docker or Kubernetes, the `data/` directory must be mapped to a persistent volume. This directory stores the operational state of the application:
- `data/raw/`, `data/processed/`, and `data/analytics/`: Built data lakes.
- `data/state/`: Incremental sync cursors for the collector.
- `data/ai/`: Persistent chat histories and AI summaries.
- `data/config/layouts/`: User-saved dashboard layouts.

### Streamlit Scope
The [Streamlit](https://streamlit.io/) dashboard is designed for **internal team use**, corporate VPNs, or local-only viewing. It includes a basic password lock for admin actions (like deleting items) but is not designed or hardened to be exposed directly to the public internet without an external authentication proxy (like Cloudflare Access or OAuth2-Proxy).

## Configuration Files

### Environment Variables

Copy the provided template and fill in your values:

```bash
cp .env.example .env
```

Required for live GitLab sync:

| Variable | Description | Required For |
|---|---|---|
| `GITLAB_URL` | GitLab instance URL (e.g. `https://gitlab.com`) | Live Sync |
| `GITLAB_TOKEN` | Personal access token with `read_api` scope | Live Sync |
| `PROJECT_IDS` | Comma-separated project IDs to sync | Live Sync |
| `ADMIN_PASSWORD` | Password for destructive dashboard actions (default: `admin`) | Optional |
| `OLLAMA_ENDPOINT` | Local or remote Ollama API URL (default: `http://localhost:11434`) | Optional |

`tools/seeder.py` generates synthetic local Parquet files directly in `data/processed/` and does not require a GitLab connection. The example config file (`default.yaml`) ships with an empty `project_ids` list to act as a global fallback, meaning it is perfectly safe to use on a fresh clone. You must supply your own `PROJECT_IDS` (via `.env`) to process live data, or use the local seeded data.

### Reset and Recreate Local Seeded Data

If you want to discard the synthetic local dataset and generate a fresh one with more realistic totals, delete the seeded outputs and run the seeder again:

```bash
# Remove seeded Layer 1 files (adjust project IDs to match your seed)
rm -f data/processed/issues_101.parquet data/processed/issues_102.parquet data/processed/issues_103.parquet

# Optionally clear Layer 2 analytics output
rm -f data/analytics/*.parquet

# Optionally reset collector sync state
rm -f data/state/sync_state.json

# Recreate local seeded data with more volume
uv run python tools/seeder.py --count 5000 --inject-errors --seed 42

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

By default, `project_ids` is empty — the rules apply globally to all projects. Add specific IDs only when you need per-project rule overrides via additional YAML files.

## Security

Before deploying or sharing your instance, consider these core security principles:

- **Secrets Management**: Your `.env` file contains sensitive tokens. It must **never** be committed to version control. The repository ignores it by default.
- **Least Privilege**: The required `GITLAB_TOKEN` only needs the `read_api` scope. No write permissions are necessary or requested by the collector.
- **Data Privacy**: All AI interactions, summaries, and chat histories are processed by the configured `OLLAMA_ENDPOINT`. If you use the default local Ollama installation (`http://localhost:11434`), your data never leaves your infrastructure. However, if you configure a proxy pointing to a cloud LLM provider, your chat histories and issue data will be sent to that external service. All generated summaries and histories are persisted locally in `data/ai/`.

## AI Assistant

GitLab Pulse includes a **local AI assistant** powered by [Ollama](https://ollama.com/). This enables context-aware issue summarization and chat without sending data to external APIs.

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

## Troubleshooting

### Common Setup Failures

- **Missing `.env` file**: If you forget to run `cp .env.example .env`, the collector cannot authenticate with GitLab. Live syncs will fail.
- **Empty Dashboard (No Data)**: The dashboard reads from pre-calculated Parquet files. If your dashboard is empty, you either haven't fetched data (`app/collector/orchestrator.py`) or haven't processed it (`app/processor/main.py`). For synthetic data, run `tools/seeder.py` first.
- **GitLab 401 Unauthorized**: Your `GITLAB_TOKEN` in `.env` is invalid, expired, or missing the `read_api` scope.
- **AI Assistant "Connection Refused"**: The dashboard expects Ollama to be running at the configured `OLLAMA_ENDPOINT` (default: `http://localhost:11434`). Ensure you ran `ollama serve` and pulled a model.
- **Data Loss on Restart**: If you run this in a container and lose synced issues or chat history on restart, ensure the `data/` directory is mapped to a persistent volume.

## Q&A

### Data Inclusion Logic
**Q: What are "Backlog" items?**
**A:** "Backlog" is the default classification for any issue that **does not match** any specific workflow stage defined in `rules.yaml`. These issues are considered `waiting` (Inventory) and have not yet entered the active development process.

### Multi-Context Issues
**Q: What if an issue belongs to multiple contexts (e.g., "R&D" and "Customer")?**
**A:**
- **Metrics & Charts**: The issue is counted **only once** (deduplicated).
- **Issue Table**: The issue appears **twice** (or more), once for each context, allowing you to see it in every relevant slice.

## License

MIT
