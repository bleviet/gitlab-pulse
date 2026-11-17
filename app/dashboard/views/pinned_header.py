"""Keeps the Overview's pinned rows stacked while the page scrolls.

Pinned, from the top: the Analytics workflow-state row (only in Analytics),
the board's toolbar and filter chips, and the board's lane headers. Their
heights depend on the screen and on the active filters, so CSS alone cannot
place each one below the previous one. The script below measures them and sets
CSS variables for the theme CSS:

- ``--pulse-pin-top``: below the workflow-state row (or the header bar).
- ``--pulse-board-top``: below the board's toolbar and chips.
- ``--pulse-lanes-top``: below the lane headers.
- ``--pulse-below-lanes``: the page content below the lanes.

The lanes take the window height between the last two, so with the page
scrolled to the bottom a whole lane is on the screen, right below the pinned
rows.

The lane headers' row cannot scroll sideways itself; the script keeps it in
step with the lanes' row, which can.
"""

import streamlit as st

_PIN_SCRIPT = """
<script>
(() => {
  if (window.__pulsePinned) return;
  window.__pulsePinned = true;
  const stickyChild = (parent, key) =>
    [...document.querySelectorAll(`${parent} > *`)].find(
      (element) => element.matches(key) || element.querySelector(`:scope > ${key}`)
    );
  const update = () => {
    const root = document.documentElement.style;
    const workflow = stickyChild(".st-key-analytics_flow", ".st-key-analytics_workflow");
    const head = stickyChild(".st-key-issue_panel", ".st-key-issue_panel_head");
    const heads = stickyChild(".st-key-issue_board_wrap", '[class*="-ibheads"]');
    const pin = workflow ? workflow.offsetHeight : 0;
    const board = pin + (head ? head.offsetHeight : 0);
    root.setProperty("--pulse-pin-top", `calc(2.5rem + ${pin}px)`);
    root.setProperty("--pulse-board-top", `calc(2.5rem + ${board}px)`);
    root.setProperty(
      "--pulse-lanes-top", `calc(2.5rem + ${board + (heads ? heads.offsetHeight : 0)}px)`
    );
    const lane = document.querySelector(
      '[data-testid="stLayoutWrapper"]:has(> [class*="issue_board-iblane"])'
    );
    const main = document.querySelector('[data-testid="stMain"]');
    if (lane && main) {
      const laneBottom = lane.getBoundingClientRect().bottom
        - main.getBoundingClientRect().top + main.scrollTop;
      root.setProperty(
        "--pulse-below-lanes", `${Math.max(0, Math.round(main.scrollHeight - laneBottom))}px`
      );
    }
  };
  const lanesRow = '.st-key-issue_board_wrap [data-testid="stHorizontalBlock"]';
  document.addEventListener("scroll", (event) => {
    const target = event.target;
    if (target instanceof Element && target.matches(lanesRow)
        && !target.closest('[class*="-ibheads"]')) {
      const heads = document.querySelector(
        '[class*="-ibheads"] [data-testid="stHorizontalBlock"]'
      );
      if (heads) heads.scrollLeft = target.scrollLeft;
    }
    update();
  }, { capture: true, passive: true });
  window.addEventListener("resize", update);
  // Filters change the toolbar's height without a scroll.
  setInterval(update, 500);
  update();
})();
</script>
"""


def inject_pinned_header_script() -> None:
    """Add the script once per page (it guards against running twice)."""
    st.html(_PIN_SCRIPT, unsafe_allow_javascript=True)
