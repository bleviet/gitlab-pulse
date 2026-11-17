"""Inline issue search in the board's toolbar (Ctrl/Cmd+K).

The search is a field in the toolbar, not a separate panel: it is compact
until it gets focus (a click, or Ctrl/Cmd+K anywhere on the page), then widens
in place. The board filters as the user types; the matching is fuzzy (see
``issue_data._build_issue_search_mask``). Esc leaves the field; it stays wide
while it holds a search.

The field is ``st_keyup`` (Streamlit's own text input only reports on Enter or
blur), which renders its input in a same-origin iframe. The script below
therefore focuses the input inside the iframe, styles it to match the
toolbar, and marks the field's container while it has focus
(``data-active``; CSS ``:focus-within`` does not see focus inside an iframe)
or holds text (``data-filled``), so the CSS can widen it.
"""

import streamlit as st
from st_keyup import st_keyup

_SEARCH_SCRIPT = """
<script>
(() => {
  if (window.__pulseSearchKeys) return;
  window.__pulseSearchKeys = true;
  const box = () => document.querySelector(".st-key-issue_search_box");
  const frame = () => box() && box().querySelector("iframe");
  const input = () => {
    const element = frame();
    return element && element.contentDocument
      && element.contentDocument.querySelector("input");
  };
  const mark = () => {
    const container = box();
    const field = input();
    if (!container || !field) return;
    container.toggleAttribute("data-filled", field.value.trim() !== "");
    container.toggleAttribute("data-active", field.ownerDocument.activeElement === field);
  };
  const focusSearch = (event) => {
    if (!((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k")) return;
    const field = input();
    if (!field) return;
    event.preventDefault();
    field.focus();
    field.select();
  };
  document.addEventListener("keydown", focusSearch, true);
  // The input's look, inside the iframe: a pill like the toolbar's buttons.
  const STYLE = `
    label, [data-testid="stWidgetLabel"] { display: none !important; }
    body { margin: 0; background: transparent; }
    input {
      box-sizing: border-box; height: 32px !important; width: 100%;
      border-radius: 999px !important; font-size: 14px !important;
      padding: 0 12px 0 34px !important;
      background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%23888'%3E%3Cpath d='M15.5 14h-.79l-.28-.27A6.47 6.47 0 0 0 16 9.5 6.5 6.5 0 1 0 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z'/%3E%3C/svg%3E") !important;
      background-repeat: no-repeat !important; background-position: 11px center !important;
      background-size: 17px 17px !important;
    }
    div:has(> input) { border-radius: 999px !important; height: 32px !important; }
  `;
  new MutationObserver(() => {
    const element = frame();
    const doc = element && element.contentDocument;
    if (!doc || !doc.body) return;
    const field = doc.querySelector("input");
    if (!field || field.__pulseSearch) return;
    field.__pulseSearch = true;
    const style = doc.createElement("style");
    style.textContent = STYLE;
    doc.head.appendChild(style);
    // Keys typed in the iframe do not reach this document.
    doc.addEventListener("keydown", (event) => {
      if (event.key === "Escape") field.blur();
      focusSearch(event);
    });
    for (const type of ["input", "focus", "blur"]) field.addEventListener(type, mark);
    mark();
  }).observe(document.body, { childList: true, subtree: true });
  // The component also sets the text itself (a search from the URL).
  setInterval(mark, 500);
})();
</script>
"""


def shortcut_label() -> str:
    """Return the platform's search shortcut, from the browser's user agent."""
    user_agent = str(st.context.headers.get("User-Agent", ""))
    return "⌘K" if "Macintosh" in user_agent or "Mac OS" in user_agent else "Ctrl K"


def render_search_box(query: str, version: int) -> str:
    """Render the search field and return its trimmed text.

    The field reports an edit only when it is rendered, which is after the
    board was filtered in that run; the caller reruns when the text differs
    from ``query``.

    Args:
        query: The current search text.
        version: Part of the widget key; the caller bumps it when the search
            changes elsewhere (a removed chip, the URL), so the field shows
            the new text instead of what was typed before.
    """
    with st.container(key="issue_search_box"):
        typed = st_keyup(
            "Search issues",
            value=query,
            placeholder=f"Search issues  {shortcut_label()}",
            key=f"issue_search_query_{version}",
            debounce=250,
            label_visibility="collapsed",
        )
    return str(typed or "").strip()


def inject_search_shortcut() -> None:
    """Add the Ctrl/Cmd+K script once per page (it guards against running twice)."""
    st.html(_SEARCH_SCRIPT, unsafe_allow_javascript=True)
