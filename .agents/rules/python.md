---
trigger: always_on
---

# Python & uv Rules

## Environment Management
- **Tooling:** STRICTLY use `uv` for all package operations.
- **Execution:** ALWAYS use `uv run <command>` (e.g., `uv run python`, `uv run pytest`).
- **Do Not:** Never attempt to source `bin/activate`. It fails in non-persistent agent shells.

## Code Standards
- **Style:** Adhere to PEP 8. Configuration in `pyproject.toml` and `mypy.ini`.
- **Type Hints:** Required for all function signatures. Use mypy for type checking.
- **Imports:** Absolute imports preferred instead of relative imports.
- **Docstrings:** Use Google-style docstrings for all public APIs.
- **Whitespace:** ALWAYS trim trailing spaces from all lines. No trailing whitespace allowed.

## Streamlit Best Practices
- **Layout sizing:** NEVER use `use_container_width=True` for charts (Plotly, Altair) or dataframes. Instead, use `width='stretch'` (or `width="stretch"`).
  - *Reason:* Streamlit has deprecated `use_container_width` for these elements and it will be removed.
  - *Exception:* `st.button` and `st.container` still use `use_container_width` or `border` arguments respectively where appropriate, check latest docs. But for `st.plotly_chart` and `st.dataframe`, strict `width="stretch"` rule applies.
