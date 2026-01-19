# GitLabInsight

A versatile analytics platform for GitLab issue data. Extracts, validates, and visualizes project metrics like Aging and Throughput using a **Clean Architecture** and **Medallion Data Pattern**.

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
- Label mappings (e.g., `type::bug` → "Bug")
- Validation rules (required labels, staleness threshold)
- Semantic colors

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
**A:** No. All metrics in the Overview, Flow, Release, and Aging pages are calculated exclusively from the **valid** dataset. Issues that fail validation (e.g., missing labels) are stripped out and do not affect operational metrics.

**Q: Do the issue lists include quality issues?**
**A:** No. The lists in Flow, Release, and Aging views show only valid issues. Invalid issues are displayed **exclusively** in the **Hygiene** view's Action Table.

### Flow View Metrics
**Q: What does "Active WIP" mean?**
**A:** It counts issues currently in a stage defined as `type: "active"` (e.g., *Architecture*, *Implementation*, *Testing*) in your `rules.yaml`. It represents work actively being processed, excluding items in "waiting" states (like *Review*).

**Q: What is "Flow Efficiency"?**
**A:** It is the ratio of meaningful work time vs. total time in the system.
$$ \text{Flow Efficiency} = \frac{\text{Active Items}}{\text{Active Items} + \text{Waiting Items}} \times 100 $$
A low efficiency (e.g., < 20%) indicates that work spends most of its time waiting (e.g., for Code Review) rather than being developed.

## License

MIT
