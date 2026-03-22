#!/usr/bin/env bash
set -e

# Enable zero-configuration local evaluations by simulating data
if [ "$SEED_LOCAL_DATA" = "true" ]; then
    echo "SEED_LOCAL_DATA is enabled. Checking if local data is needed..."
    
    # Check if processed layer data exists
    if ! ls data/processed/issues_*.parquet 1> /dev/null 2>&1; then
        echo "No data found. Seeding synthetic test data..."
        uv run python tools/seeder.py --count 1000 --inject-errors
        echo "Processing synthetic data..."
        uv run python app/processor/main.py
    else
        echo "Local data already exists. Skipping synthetic generation."
    fi
fi

echo "Starting GitLabInsight dashboard..."
exec uv run streamlit run app/dashboard/main.py --server.address=0.0.0.0
