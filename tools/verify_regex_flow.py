import pandas as pd
import re
import sys
import os
import numpy as np

# Load processed data
file_path = "data/analytics/issues_valid.parquet"
if not os.path.exists(file_path):
    print(f"File not found: {file_path}")
    sys.exit(1)

df = pd.read_parquet(file_path)

print(f"Total issues: {len(df)}")
if "labels" not in df.columns:
    print("No labels column found")
    sys.exit(1)

def has_iteration(labels):
    if not isinstance(labels, list) and not isinstance(labels, np.ndarray):
        return False
    return any(re.match(r"^iteration-\d+$", l) for l in labels)

def has_verify(labels):
    if not isinstance(labels, list) and not isinstance(labels, np.ndarray):
        return False
    return any(re.match(r"^iteration-\d+::verify$", l) for l in labels)

iteration_issues = df[df["labels"].apply(has_iteration)]
verify_issues = df[df["labels"].apply(has_verify)]

print(f"Found {len(iteration_issues)} iteration issues")
print(f"Found {len(verify_issues)} verification issues")

# Filter out issues that are explicitly Done (legacy data might have conflicting labels)
def is_done_label(labels):
    if not isinstance(labels, list) and not isinstance(labels, np.ndarray):
        return False
    return "workflow::done" in labels or "status::released" in labels

# Only verify issues that are NOT explicitly done AND are open
active_iteration_issues = iteration_issues[
    ~iteration_issues["labels"].apply(is_done_label) & (iteration_issues["state"] == "opened")
]
active_verify_issues = verify_issues[
    ~verify_issues["labels"].apply(is_done_label) & (verify_issues["state"] == "opened")
]

print(f"Active Iteration Issues (Open & Not Done): {len(active_iteration_issues)}")
print(f"Active Verification Issues (Open & Not Done): {len(active_verify_issues)}")

# Check stages
in_progress = active_iteration_issues[active_iteration_issues["stage"] == "In Progress"]
verification = active_verify_issues[active_verify_issues["stage"] == "Verification"]

print(f"In Progress: {len(in_progress)}")
print(f"Verification: {len(verification)}")

if len(active_iteration_issues) == 0 and len(active_verify_issues) == 0:
    print("WARNING: No active iteration issues found to verify. This might be chance.")
else:
    if len(in_progress) != len(active_iteration_issues):
        print("ERROR: Not all active iteration issues are In Progress")
        print(active_iteration_issues[active_iteration_issues["stage"] != "In Progress"][["title", "labels", "stage"]])
        sys.exit(1)
        
    if len(verification) != len(active_verify_issues):
        print("ERROR: Not all active verification issues are Verification")
        print(active_verify_issues[active_verify_issues["stage"] != "Verification"][["title", "labels", "stage"]])
        sys.exit(1)

print("SUCCESS")
