"""Keep Plotly click selection working right after a dialog closes.

Plotly selects the point under the cursor from its hover state, which only
updates on mouse movement. Overview charts are rebuilt while a dialog covers
them, so after the dialog closes, a chart under a stationary cursor has no hover
state and ignores the first click. This script replays a ``mousemove`` at the
last cursor position when a dialog closes, so that first click selects.
"""

import streamlit as st

_SCRIPT = """
<script>
(() => {
  if (window.__pulsePointerRefresh) return;
  window.__pulsePointerRefresh = true;
  let last = null;
  let dialogOpen = false;
  document.addEventListener("pointermove", (e) => { last = [e.clientX, e.clientY]; }, true);
  new MutationObserver(() => {
    const open = document.querySelector('[data-testid="stDialog"]') !== null;
    if (dialogOpen && !open && last) {
      requestAnimationFrame(() => {
        const target = document.elementFromPoint(last[0], last[1]);
        if (target) {
          target.dispatchEvent(new MouseEvent("mousemove", {
            clientX: last[0], clientY: last[1], bubbles: true,
          }));
        }
      });
    }
    dialogOpen = open;
  }).observe(document.body, { childList: true, subtree: true });
})();
</script>
"""


def inject_pointer_refresh() -> None:
    """Install the dialog-close pointer refresh script once per page."""
    st.html(_SCRIPT, unsafe_allow_javascript=True)
