import pandas as pd
import sys
import os

# Load processed data
file_path = "data/analytics/issues_valid.parquet"
if not os.path.exists(file_path):
    print(f"File not found: {file_path}")
    sys.exit(1)

df = pd.read_parquet(file_path)

total_rows = len(df)
unique_ids = df["id"].nunique()

print(f"Total Rows: {total_rows}")
print(f"Unique Issues: {unique_ids}")

if total_rows > unique_ids:
    print(f"SUCCESS: Found {total_rows - unique_ids} duplicate rows due to multi-context.")
    
    # Show an example of a duplicated issue
    dupes = df[df.duplicated(subset=["id"], keep=False)]
    if not dupes.empty:
        example_id = dupes.iloc[0]["id"]
        print(f"\nExample Issue ID {example_id}:")
        print(dupes[dupes["id"] == example_id][["title", "context", "context_group"]])
else:
    print("WARNING: No duplicates found. Seeder might not have generated multi-context issues yet.")
    # This isn't necessarily a failure of the code, just the random chance of the seeder.
    # But we want to confirm it happens.
