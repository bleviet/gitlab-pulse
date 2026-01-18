"""GraphQL client for GitLab Work Item hierarchy resolution.

Uses httpx for batch queries to resolve parent-child links.
"""

import logging
import os
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

# GraphQL query for work item hierarchy
WORK_ITEMS_QUERY = """
query GetWorkItems($fullPath: ID!, $iids: [String!]) {
  project(fullPath: $fullPath) {
    workItems(iids: $iids, first: 100) {
      nodes {
        iid
        workItemType {
          name
        }
        widgets {
          ... on WorkItemWidgetHierarchy {
            parent {
              iid
            }
            children {
              nodes {
                iid
              }
            }
          }
        }
      }
    }
  }
}
"""


class GqlClient:
    """GraphQL client for GitLab Work Item hierarchy resolution.

    Resolves parent-child relationships that are not available via REST API.
    """

    def __init__(
        self,
        gitlab_url: Optional[str] = None,
        private_token: Optional[str] = None,
    ) -> None:
        """Initialize the GraphQL client.

        Args:
            gitlab_url: GitLab instance URL (default: GITLAB_URL env var)
            private_token: GitLab private token (default: GITLAB_TOKEN env var)
        """
        self.gitlab_url = gitlab_url or os.environ.get("GITLAB_URL", "https://gitlab.com")
        self.private_token = private_token or os.environ.get("GITLAB_TOKEN", "")

        if not self.private_token:
            raise ValueError("GITLAB_TOKEN environment variable is required")

        self.graphql_url = f"{self.gitlab_url.rstrip('/')}/api/graphql"
        self.headers = {
            "Authorization": f"Bearer {self.private_token}",
            "Content-Type": "application/json",
        }

    def fetch_hierarchy(
        self,
        project_path: str,
        iids: list[int],
    ) -> dict[int, dict[str, Any]]:
        """Fetch work item hierarchy for a list of issue IIDs.

        Args:
            project_path: Full project path (e.g., "group/project")
            iids: List of issue IIDs to query

        Returns:
            Dict mapping IID to hierarchy data:
            {iid: {"work_item_type": str, "parent_id": int|None, "child_ids": list[int]}}
        """
        if not iids:
            return {}

        # Batch queries in groups of 100
        results: dict[int, dict[str, Any]] = {}
        batch_size = 100

        for i in range(0, len(iids), batch_size):
            batch_iids = iids[i : i + batch_size]
            batch_results = self._query_batch(project_path, batch_iids)
            results.update(batch_results)

        return results

    def _query_batch(
        self,
        project_path: str,
        iids: list[int],
    ) -> dict[int, dict[str, Any]]:
        """Execute a single batch query."""
        variables = {
            "fullPath": project_path,
            "iids": [str(iid) for iid in iids],
        }

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    self.graphql_url,
                    headers=self.headers,
                    json={"query": WORK_ITEMS_QUERY, "variables": variables},
                )
                response.raise_for_status()
                data = response.json()

            if "errors" in data:
                logger.warning(f"GraphQL errors: {data['errors']}")
                return {}

            return self._parse_response(data)

        except httpx.HTTPError as e:
            logger.error(f"GraphQL request failed: {e}")
            return {}

    def _parse_response(self, data: dict[str, Any]) -> dict[int, dict[str, Any]]:
        """Parse GraphQL response into hierarchy dict."""
        results: dict[int, dict[str, Any]] = {}

        project = data.get("data", {}).get("project")
        if not project:
            return results

        work_items = project.get("workItems", {}).get("nodes", [])

        for item in work_items:
            iid = int(item.get("iid", 0))
            work_item_type = item.get("workItemType", {}).get("name", "ISSUE")

            parent_id: Optional[int] = None
            child_ids: list[int] = []

            for widget in item.get("widgets", []):
                if "parent" in widget:
                    parent = widget.get("parent")
                    if parent:
                        parent_id = int(parent.get("iid", 0))

                if "children" in widget:
                    children = widget.get("children", {}).get("nodes", [])
                    child_ids = [int(c.get("iid", 0)) for c in children]

            results[iid] = {
                "work_item_type": work_item_type,
                "parent_id": parent_id,
                "child_ids": child_ids,
            }

        return results
