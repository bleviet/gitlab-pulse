# GitLabInsight

A versatile analytics platform for GitLab issue data. Extracts, validates, and visualizes project metrics like Aging and Throughput using a **Clean Architecture** and **Medallion Data Pattern**.

## Quick Start

```bash
# Install dependencies
uv sync --dev

# Generate synthetic test data
uv run python tools/seeder.py --count 1000 --inject-errors

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
| **L3** | `app/dashboard/` | Streamlit visualization |

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

## License

MIT
