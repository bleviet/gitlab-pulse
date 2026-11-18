# Layer 3 Rewrite Documentation (FastAPI + React/TypeScript)

This directory documents the `feat/fastapi-react-dashboard` branch, which replaces the Streamlit presentation layer (`app/dashboard/`) with a FastAPI API server and a React/TypeScript single-page application (`frontend/`).

The documentation is organized using the **Diataxis** framework so each document serves one clear purpose:

| Quadrant | Orientation | Document | Use when you want to |
|---|---|---|---|
| **Tutorials** | Learning-oriented | [tutorial.md](tutorial.md) | Follow a hands-on walkthrough from seeding synthetic data to using Analytics, Compact, and Admin views |
| **How-to Guides** | Goal-oriented | [how-to.md](how-to.md) | Accomplish a specific task: run dev servers, run test suites, add a field or facet, override colors, or deploy with Docker |
| **Reference** | Information-oriented | [reference.md](reference.md) | Look up exact module inventories, HTTP API contracts, Pydantic/TypeScript schemas, URL parameters, and removed files |
| **Explanation** | Understanding-oriented | [explanation.md](explanation.md) | Understand why Streamlit was replaced, why the new architecture is structured this way, and the trade-offs involved |
