Here is the precise **View Specification** for the Faceted Cumulative Flow Diagram in the Overview page. This description is intended for a frontend engineer or data visualization specialist using libraries like Matplotlib, Plotly, or D3.js.

### **1. Layout Architecture: Small Multiples**

* **Grid Structure:** 3 Rows × 1 Column.
* **Vertical Ordering:**
1. **Top Panel:** Features (Business Value)
2. **Middle Panel:** Bugs (Quality/Debt)
3. **Bottom Panel:** Tasks (Operational Overhead)


* **Alignment:** All three panels **must share the exact same X-Axis (Time)**.
* *Why:* This allows the user to vertically scan and correlate events (e.g., "Did a spike in Bugs on week 4 cause the drop in Features on week 5?").


* **Sizing:** All panels should have equal height (1:1:1 ratio) to give equal visual weight to all types of work.

### **2. Chart Type: Stacked Area / Filled Line**

Each of the three panels follows the same internal plotting logic.

* **X-Axis:** Time (Daily or Weekly buckets).
* **Y-Axis:** Count of Issues (Integer).
* **Scaling:** Y-Axes must be **independent** (unlinked).
* *Why:* Feature counts might range from 0–100, while Bugs might range from 0–20. Forcing them to the same scale would flatten the Bug chart, hiding vital volatility patterns.


* **Plotting Layers (Z-Index Order):**
1. **Background Layer (Total Scope):** A line plotting `Total Created`. The area below this line represents the total known scope.
2. **Foreground Layer (Completed Work):** A filled area plotting `Total Closed`. This sits *on top* of the background layer.
3. **The Resulting "Gap" (WIP):** The visible space between the "Total Created" line and the "Total Closed" filled area represents **Work In Progress (Inventory)**.



### **3. Semantic Color Palette**

Use color to trigger immediate cognitive recognition of the work type.

| Panel | Primary Theme | Fill Color (Closed) | Area Color (WIP/Open) | Rationale |
| --- | --- | --- | --- | --- |
| **FEATURES** | **Cool / Growth** | **Dark Green** (or Blue) | **Light Green** (or Light Blue) | Green associations with "Go", "Money", and "Growth." |
| **BUGS** | **Warm / Alert** | **Dark Red** | **Light Red / Pink** | Red associations with "Stop", "Error", and "Heat." |
| **TASKS** | **Neutral / Passive** | **Dark Grey** | **Light Grey** | Grey associations with "Background", "Concrete", and "Structure." |

### **4. Axes & Labels**

* **Titles:** Left-aligned, bold.
* `Features (Value Flow)`
* `Bugs (Failure Demand)`
* `Tasks (Maintenance)`


* **X-Axis Ticks:** Show dates only on the **Bottom Panel** to reduce visual clutter (Edward Tufte's "Data-Ink Ratio").
* **Gridlines:** Horizontal gridlines only (light opacity) to assist in reading volume levels. Vertical gridlines are optional/distracting.

### **5. Interactive Elements (If using a web-based library like Plotly/D3)**

* **Synced Hover:** Hovering over a specific week on the "Features" graph should display the vertical "crosshair" line on the "Bugs" and "Tasks" graphs simultaneously.
* **Tooltip Content:**
* Date: `[Week Start Date]`
* Total Created: `[Integer]`
* Total Closed: `[Integer]`
* **Net WIP:** `[Created - Closed]` (Calculated field, vital for quick assessment).



### **6. Visual "Smell Tests" (Quality Assurance for the View)**

* **The "Wedge" Check:** In the Features graph, the "Closed" area should generally form an upward wedge. If the lines are parallel, velocity is zero.
* **The "Jaws" Check:** In the Bug graph, if the "Total Created" line (top jaw) pulls away sharply from the "Total Closed" line (bottom jaw), the view effectively highlights a "Bug Explosion."
