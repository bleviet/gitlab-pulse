"""Live GitLab Data Seeder.

Populates a REAL GitLab repository with synthetic test data.
WARNING: This tool performs WRITE operations. Use only on empty test projects.
"""

import argparse
import logging
import os
import random
import sys
import time
from datetime import datetime, timedelta
from typing import Optional

import gitlab
import requests
from faker import Faker
from dotenv import load_dotenv

# Load env vars
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("gitlab_seeder")
fake = Faker()

# Configuration Constants
LABELS = {
    "type::bug": "#d9534f",
    "type::feature": "#5cb85c",
    "type::task": "#5bc0de",
    "severity::critical": "#ff0000",
    "severity::high": "#d9534f",
    "severity::medium": "#f0ad4e",
    "severity::low": "#5bc0de",
    "priority::1": "#ff0000",
    "priority::2": "#f0ad4e",
    "priority::3": "#5bc0de",
    "workflow::architecture": "#5843ad",
    "workflow::implementation": "#428bca",
    "workflow::review": "#f0ad4e",
    "workflow::test": "#5bc0de",
    "workflow::done": "#5cb85c",
    "rnd::Alpha": "#6610f2",  # Purple for Context Alpha
    "rnd::Beta": "#20c997",   # Teal for Context Beta
    "cust::Gamma": "#d63384", # Pink for Customer Gamma
    "iteration-1": "#6f42c1", # Purple
    "iteration-2": "#6f42c1",
    "iteration-3": "#6f42c1",
    "iteration-1::verify": "#fd7e14", # Orange
    "iteration-2::verify": "#fd7e14",
    "iteration-3::verify": "#fd7e14",
}

MILESTONES = [
    {"title": "v1.0", "offset_start": -60, "duration": 30},
    {"title": "v1.1", "offset_start": -30, "duration": 30},
    {"title": "v1.2", "offset_start": 0, "duration": 30},  # Current
    {"title": "v1.3", "offset_start": 30, "duration": 30},
]


def get_gitlab_client() -> gitlab.Gitlab:
    """Initialize GitLab client from environment variables."""
    url = os.getenv("GITLAB_URL", "https://gitlab.com")
    token = os.getenv("GITLAB_TOKEN")
    
    if not token:
        logger.error("GITLAB_TOKEN environment variable is not set.")
        sys.exit(1)
        
    return gitlab.Gitlab(url, private_token=token)


def setup_labels(project) -> None:
    """Create standard labels if they don't exist."""
    logger.info("Setting up labels...")
    existing = {l.name: l for l in project.labels.list(all=True)}
    
    for name, color in LABELS.items():
        if name not in existing:
            logger.info(f"Creating label: {name}")
            try:
                project.labels.create({"name": name, "color": color})
            except Exception as e:
                logger.warning(f"Failed to create label {name}: {e}")
        else:
            logger.debug(f"Label {name} already exists.")


def setup_milestones(project) -> list[object]:
    """Create standard milestones and return them."""
    logger.info("Setting up milestones...")
    existing = {m.title: m for m in project.milestones.list(all=True)}
    active_milestones = []
    
    now = datetime.now()
    
    for ms_config in MILESTONES:
        title = ms_config["title"]
        start_date = now + timedelta(days=ms_config["offset_start"])
        due_date = start_date + timedelta(days=ms_config["duration"])
        
        # Convert to YYYY-MM-DD string
        start_str = start_date.strftime("%Y-%m-%d")
        due_str = due_date.strftime("%Y-%m-%d")
        
        if title not in existing:
            logger.info(f"Creating milestone: {title}")
            try:
                ms = project.milestones.create({
                    "title": title,
                    "start_date": start_str,
                    "due_date": due_str
                })
                active_milestones.append(ms)
            except Exception as e:
                logger.warning(f"Failed to create milestone {title}: {e}")
        else:
            active_milestones.append(existing[title])
            
    return active_milestones


def generate_issue_payload(milestones: list, parent_iid: Optional[int] = None, inject_errors: bool = False) -> dict:
    """Generate a valid issue payload."""
    issue_labels = []
    
    # Error Injection: Missing Labels (5%)
    if inject_errors and random.random() < 0.05:
        # Create an issue with NO labels (invalid)
        return {
            "title": f"Quality: Issue with missing labels {fake.word()}",
            "description": "This issue should be flagged by the validator.",
            "labels": [],
            "milestone_id": None,
            "issue_type": "issue",
            "created_at": datetime.now().isoformat()
        }

    # Error Injection: Conflicting Labels (1%)
    if inject_errors and random.random() < 0.01:
        # Create an issue with both Bug and Feature (invalid)
        return {
            "title": f"Quality: Conflicting labels {fake.word()}",
            "description": "This issue has both Bug and Feature types.",
            "labels": ["type::bug", "type::feature", "priority::1"],
            "milestone_id": None,
            "issue_type": "issue",
            "created_at": datetime.now().isoformat()
        }

    # Decide Type: 80% Issue, 20% Task (only if parent available)
    is_task = parent_iid is not None and random.random() < 0.2
    
    if is_task:
        issue_type_param = "task"
        title_prefix = "Task: "
        # Labels
        issue_labels.append("type::task")
        issue_labels.append(random.choice([k for k in LABELS if "workflow" in k]))
        issue_labels.append(random.choice([k for k in LABELS if "priority" in k]))
        
        description = fake.paragraph()
        if parent_iid:
            description += f"\n\nParent: #{parent_iid}"
            
    else:
        issue_type_param = "issue"
        # Standard Issue logic...
        type_label = random.choice(["type::bug", "type::feature"])
        issue_labels.append(type_label)
        
        # Error Injection: Missing Severity/Priority (10%)
        skip_attributes = inject_errors and random.random() < 0.10

        if type_label == "type::bug":
            title_prefix = "Bug: "
            if not skip_attributes:
                issue_labels.append(random.choice([k for k in LABELS if "severity" in k]))
        else:
            title_prefix = "Feat: "
            
        if not skip_attributes:
            issue_labels.append(random.choice([k for k in LABELS if "priority" in k]))
            
        if not skip_attributes:
            issue_labels.append(random.choice([k for k in LABELS if "priority" in k]))
            
        # Iteration Flow (30% chance) vs Standard Workflow
        if random.random() < 0.3:
             # Either just iteration (active) or iteration::verify (waiting)
             issue_labels.append(random.choice([k for k in LABELS if "iteration" in k]))
        else:
             # Standard Flow
             issue_labels.append(random.choice([k for k in LABELS if "workflow" in k]))
        
        # Add Context Label (50% chance)
        if random.random() < 0.5:
             # Pick 1 or 2 context labels to simulate multi-context issues
             start_labels = [k for k in LABELS if "rnd::" in k or "cust::" in k]
             # Shuffle and pick 1 or 2
             random.shuffle(start_labels)
             num_contexts = 1 if random.random() < 0.8 else 2
             issue_labels.extend(start_labels[:num_contexts])
             
        description = fake.paragraph()

    # Milestone (Tasks can have milestones too)
    milestone_id = None
    if milestones and random.random() < 0.8:
        ms = random.choice(milestones)
        milestone_id = ms.id
        
    return {
        "title": f"{title_prefix}{fake.sentence(nb_words=6)}",
        "description": description,
        "labels": issue_labels,
        "milestone_id": milestone_id,
        "issue_type": issue_type_param, # Support native type
        "created_at": (datetime.now() - timedelta(days=random.randint(0, 60))).isoformat()
    }



def link_work_items_gql(child_numeric_id: int, parent_numeric_id: int, project_path: str, token: str) -> bool:
    """Link two work items using GraphQL mutation."""
    url = "https://gitlab.com/api/graphql"
    headers = {"Authorization": f"Bearer {token}"}
    
    # Construct GIDs (assuming WorkItem GID matches Issue ID for these new items)
    child_gid = f"gid://gitlab/WorkItem/{child_numeric_id}"
    parent_gid = f"gid://gitlab/WorkItem/{parent_numeric_id}"
    
    mutation = """
    mutation($id: WorkItemID!, $parentId: WorkItemID) {
      workItemUpdate(input: {id: $id, hierarchyWidget: {parentId: $parentId}}) {
        errors
      }
    }
    """
    
    try:
        resp = requests.post(
            url,
            json={
                "query": mutation, 
                "variables": {"id": child_gid, "parentId": parent_gid}
            },
            headers=headers
        )
        data = resp.json()
        errors = data.get("data", {}).get("workItemUpdate", {}).get("errors", [])
        if errors:
            logger.error(f"  -> GraphQL Linking failed: {errors}")
            return False
        return True
    except Exception as e:
        logger.error(f"  -> GraphQL Request failed: {e}")
        return False



def link_work_items_gql(child_numeric_id: int, parent_numeric_id: int, project_path: str, token: str) -> bool:
    """Link two work items using GraphQL mutation."""
    url = "https://gitlab.com/api/graphql"
    headers = {"Authorization": f"Bearer {token}"}
    
    # Construct GIDs (assuming WorkItem GID matches Issue ID for these new items)
    # NOTE: This assumes issue.id matches the WorkItem ID. 
    # Use the 'id' field from the issue object, NOT 'iid'.
    child_gid = f"gid://gitlab/WorkItem/{child_numeric_id}"
    parent_gid = f"gid://gitlab/WorkItem/{parent_numeric_id}"
    
    mutation = """
    mutation($id: WorkItemID!, $parentId: WorkItemID) {
      workItemUpdate(input: {id: $id, hierarchyWidget: {parentId: $parentId}}) {
        errors
      }
    }
    """
    
    try:
        resp = requests.post(
            url,
            json={
                "query": mutation, 
                "variables": {"id": child_gid, "parentId": parent_gid}
            },
            headers=headers
        )
        data = resp.json()
        errors = data.get("data", {}).get("workItemUpdate", {}).get("errors", [])
        if errors:
            logger.error(f"  -> GraphQL Linking failed: {errors}")
            return False
        return True
    except Exception as e:
        logger.error(f"  -> GraphQL Request failed: {e}")
        return False


def seed_issues(project, count: int, milestones: list, inject_errors: bool = False) -> None:
    """Create synthetic issues."""
    logger.info(f"Seeding {count} issues (Errors: {inject_errors})...")
    
    token = os.getenv("GITLAB_TOKEN")
    project_path = project.path_with_namespace
    
    # Store tuples of (id, iid) for parents
    potential_parents = []
    
    for i in range(count):
        # Pick a parent if available
        parent_data = None
        parent_iid = None
        parent_id = None
        
        if potential_parents:
            parent_data = random.choice(potential_parents)
            parent_iid = parent_data['iid']
            parent_id = parent_data['id']
            
        payload = generate_issue_payload(milestones, parent_iid, inject_errors)
        
        try:
            issue = project.issues.create(payload)
            logger.info(f"Created issue #{issue.iid} ({payload['issue_type']}): {issue.title}")
            
            # If it's a standard issue, add to parents list
            if payload["issue_type"] == "issue":
                potential_parents.append({'id': issue.id, 'iid': issue.iid})
            
            # Link to parent if applicable (Only Tasks can have parents in this schema)
            if parent_id and payload["issue_type"] == "task":
                success = link_work_items_gql(issue.id, parent_id, project_path, token)
                if success:
                    logger.info(f"  -> Linked to parent #{parent_iid} via GraphQL")
                else:
                    logger.warning(f"  -> Failed to link parent #{parent_iid}")

            # Simulate state (Closed/Open)
            if random.random() < 0.5:
                issue.state_event = "close"
                issue.save()
                
            time.sleep(0.5)
            
        except Exception as e:
            logger.error(f"Failed to create issue: {e}")


def main():
    parser = argparse.ArgumentParser(description="GitLab Live Seeder")
    parser.add_argument("--project-id", type=int, required=True, help="Target GitLab Project ID")
    parser.add_argument("--count", type=int, default=10, help="Number of issues to create")
    parser.add_argument("--force", action="store_true", help="Skip confirmation")
    parser.add_argument("--inject-errors", action="store_true", help="Inject quality errors")
    args = parser.parse_args()
    
    # Safety Check
    if not args.force:
        print(f"⚠️  WARNING: This will write data to GitLab Project ID {args.project_id}.")
        confirm = input("Are you sure? (type 'yes' to confirm): ")
        if confirm != "yes":
            print("Aborted.")
            sys.exit(0)
            
    gl = get_gitlab_client()
    
    try:
        project = gl.projects.get(args.project_id)
        logger.info(f"Connected to project: {project.name_with_namespace}")
    except Exception as e:
        logger.error(f"Could not fetch project {args.project_id}: {e}")
        sys.exit(1)
        
    setup_labels(project)
    milestones = setup_milestones(project)
    seed_issues(project, args.count, milestones, args.inject_errors)
    
    logger.info("Seeding complete! 🚀")


if __name__ == "__main__":
    main()
