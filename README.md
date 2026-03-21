# GitLabInsight

A versatile analytics platform for GitLab issue data. Extracts, validates, and visualizes workflow health and throughput using a **Clean Architecture** and **Medallion Data Pattern**.

## Quick Start

```bash
# Install dependencies
uv sync --dev


# Generate synthetic test data (Local)
uv run python tools/seeder.py --count 1000 --inject-errors

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
export PROJECT_IDS="101,102,103"
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

# Profile Layer 2 performance
uv run python -m cProfile -s time app/processor/main.py
```

## Q&A

### Data Inclusion Logic
**Q: Are quality issues included in "Open Issues" or "Bug Ratio" metrics?**
**A:** No. The operational metrics shown in the Overview and Capacity pages are calculated exclusively from the **valid** dataset. Issues that fail validation (e.g., missing labels) are stripped out and do not affect those metrics.

**Q: Do the issue lists include quality issues?**
**A:** No. The lists in the Overview and Capacity views show only valid issues. Invalid issues are displayed **exclusively** in the **Hygiene** view's Action Table.

### Flow View Metrics
**Q: What does "Active WIP" mean?**
**A:** It counts issues currently in a stage defined as `type: "active"` (e.g., *Architecture*, *Implementation*, *Testing*) in your `rules.yaml`. It represents work actively being processed, excluding items in "waiting" states (like *Review*).

**Q: What is "Flow Efficiency"?**
**A:** It is the ratio of meaningful work time vs. total time in the system.
$$ \text{Flow Efficiency} = \frac{\text{Active Items}}{\text{Active Items} + \text{Waiting Items}} \times 100 $$
A low efficiency (e.g., < 20%) indicates that work spends most of its time waiting (e.g., for Code Review) rather than being developed.

**Q: What are "Backlog" items?**
**A:** "Backlog" is the default classification for any valid issue that **does not match** any specific workflow stage defined in `rules.yaml`. These issues are considered `waiting` (Inventory) and have not yet entered the active development process.

**Q: How do I interpret the "Days in Stage (Aging)" graph?**
**A:** This **Box Plot** visualizes the distribution of time (in days) that issues have spent in their *current* stage without an update.
- **X-Axis:** Workflow Stages (e.g., *Implementation*, *Review*).
- **Y-Axis:** Days in current stage.
- **Box & Whiskers:** Shows the median time (line inside box) and variability.
- **Dots:** Outliers—issues that have been stuck significantly longer than others in the same stage.
Use this to identify **stalled work** or process bottlenecks.

### Interactive Flow Features
**Q: How do I filter the Flow charts?**
**A:** The **Work by Stage** and **Days in Stage** charts are interactive:
- **Click**: Select a single stage or segment to filter the Issue Drill-down table.
- **Shift+Click**: Select multiple segments for combined analysis.
- **Double-Click**: Reset the selection to show all data.
- **Tabs**: Switch between "Work by Stage" (Full Width) and "Days in Stage" (Full Width) to delve into different aspects of the flow without visual clutter.

### Multi-Context Issues
**Q: What if an issue belongs to multiple contexts (e.g., "R&D" and "Customer")?**
**A:**
- **Metrics & Charts**: The issue is counted **only once** (deduplicated) in global metrics like "Active WIP" and the "Work by Stage" to ensure accurate counts.
- **Issue Table**: The issue appears **twice** (or more), once for each context, allowing you to see it in every relevant slice.

### Help & Descriptions
**Q: Where can I find stage definitions?**
**A:** Hover over the bars in the **Work by Stage** chart. The tooltips now display a detailed description of each stage (e.g., "Code review and merge request feedback") as configured in your `default.yaml`. A general help icon `(?)` in the chart header also provides usage instructions.

## License

MIT
