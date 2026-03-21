---
name: local-data-manager
description: Terminal workflow for detecting, inspecting, seeding, deleting, and rebuilding local synthetic project data for dashboard testing and validation.
---

# Local Data Manager

## Purpose

The Local Data Manager provides a fast local workflow for creating, validating, resetting, and removing synthetic project data used by the dashboard.

It is designed for development and testing scenarios where you want to work with realistic issue data without depending on live GitLab API responses.

## Use this skill when

Use this skill when you need to:

- inspect which local projects already exist
- see issue totals for each detected local project
- create or reseed synthetic project data
- simulate assignment coverage and realistic team sizes
- delete selected local projects or wipe all local seeded data
- rebuild analytics after local data changes
- run a full local reset and rebuild workflow

## Entry point

Start the Local Data Manager with:

```bash
uv run python tools/local_data_manager.py
