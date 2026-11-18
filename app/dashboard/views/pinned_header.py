"""Keeps the Overview's pinned rows stacked while the page scrolls.

Pinned, from the top: the Analytics workflow-state row (only in Analytics),
the board's toolbar, filter chips and pager, and the board's lane headers. Their
heights depend on the screen and on the active filters, so CSS alone cannot
place each one below the previous one. The script below measures them and sets
CSS variables for the theme CSS:

- ``--pulse-pin-top``: below the workflow-state row (or the header bar).
- ``--pulse-heads-top``: below the board's toolbar, chips and pager (the lane
  headers are pinned here).

The Analytics workflow-state row is pinned only while it and the board's
pinned head (toolbar, chips and page bar) leave at least 15rem of the window
free below them (narrow windows stack its charts and make it tall).

The lane headers' row cannot scroll sideways itself; the script keeps it in
step with the lanes' row, which can.

The issue table's column header cannot stick either: Streamlit's grid draws
it on a canvas of its own inside the table. While that header is scrolled
under the pinned rows, the script shows a copy of the canvas, pinned below
them (``#pulse-table-head``). The copy is a picture: it does not take clicks,
so sorting is done on the table's own header.
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
  const tableHeadCopy = () => {
    let copy = document.getElementById("pulse-table-head");
    if (!copy) {
      copy = document.createElement("canvas");
      copy.id = "pulse-table-head";
      copy.style.cssText = "position:fixed; z-index:57; pointer-events:none; display:none;"
        + " box-shadow:0 10px 14px -10px rgba(0,0,0,0.25);";
      document.body.appendChild(copy);
    }
    return copy;
  };
  const pinTableHead = (top) => {
    const copy = tableHeadCopy();
    const table = document.querySelector('.st-key-issue_panel [data-testid="stDataFrame"]');
    const head = table && [...table.querySelectorAll("canvas")].find(
      (canvas) => canvas.getAttribute("data-testid") !== "data-grid-canvas"
    );
    const headBox = head && head.getBoundingClientRect();
    const tableBox = table && table.getBoundingClientRect();
    // Only while the header is under the pinned rows and rows are still shown.
    if (!head || headBox.top >= top || tableBox.bottom < top + 2 * headBox.height) {
      copy.style.display = "none";
      return;
    }
    copy.width = head.width;
    copy.height = head.height;
    copy.getContext("2d").drawImage(head, 0, 0);
    Object.assign(copy.style, {
      display: "block", left: `${headBox.left}px`, top: `${top}px`,
      width: `${headBox.width}px`, height: `${headBox.height}px`,
    });
  };
  const update = () => {
    const root = document.documentElement.style;
    const workflow = stickyChild(".st-key-analytics_flow", ".st-key-analytics_workflow");
    const head = stickyChild(".st-key-issue_panel", ".st-key-issue_panel_head");
    const rem = parseFloat(getComputedStyle(document.documentElement).fontSize);
    const headHeight = head ? head.offsetHeight : 0;
    // Pinned only while at least 15rem of the window stays free below the pinned rows.
    const fits = workflow
      && workflow.offsetHeight + headHeight <= window.innerHeight - 2.5 * rem - 15 * rem;
    if (workflow) workflow.style.position = fits ? "" : "static";
    const pin = fits ? workflow.offsetHeight : 0;
    const headsTop = pin + headHeight;
    root.setProperty("--pulse-pin-top", `calc(2.5rem + ${pin}px)`);
    root.setProperty("--pulse-heads-top", `calc(2.5rem + ${headsTop}px)`);
    pinTableHead(2.5 * rem + headsTop);
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
