# **Technical Specification: Layer 3 \- Presentation Layer**

Version: 1.1  
Reference Architecture: Architecture/layer\_3\_specification.md v1.0  
Scope: Detailed design for the Streamlit-based Dashboard, including UI/UX standards and Theming.

## **1\. UI/UX Design System**

### **1.1. Design Philosophy**

The dashboard follows a **"Modern Minimalist"** aesthetic.

* **Card-Based Layout:** Metrics and Charts are contained in visually distinct blocks.  
* **High Contrast:** Critical alerts (Stale issues) use bold colors; context (grid lines) uses subtle greys.  
* **Mode-Agnostic:** All custom visual elements must pass WCAG AA contrast standards on both dark and light backgrounds.

### **1.2. Color Palette (Semantic)**

We use a **Unified Semantic Palette** to ensure consistency across all charts. Hard-coding colors ensures that "Bugs" are always Red, regardless of the Streamlit theme.

| Category | Hex Code | Description | Usage |
| :---- | :---- | :---- | :---- |
| **Primary** | \#4F46E5 | Indigo | Main Bars, Active States, "Total Issues" |
| **Bug/Critical** | \#EF4444 | Rose/Red | Bug counts, High Severity, Error Rates |
| **Feature** | \#3B82F6 | Blue | Feature counts, "In Progress" |
| **Task/Done** | \#10B981 | Emerald | Completed items, Tasks |
| **Stale/Warn** | \#F59E0B | Amber | Stale Issues, Missing Labels |
| **Neutral** | \#64748B | Slate | Text, Grid lines, Secondary info |

### **1.3. Theme Configuration (.streamlit/config.toml)**

The application *must* include a config file to enforce the brand identity while respecting the user's system preference (Dark/Light).

\[theme\]  
primaryColor \= "\#4F46E5"  
backgroundColor \= "\#FFFFFF" \# (Light Mode Default) / Detects system pref  
secondaryBackgroundColor \= "\#F1F5F9"  
textColor \= "\#1E293B"  
font \= "sans serif"

## **2\. UI Components & Layout**

### **2.1. Global Sidebar**

* **Header:** App Title (GitLabInsight) with a minimalist icon.  
* **Domain Selector:** Populated from the team column in the Analytics parquet.  
* **Time Range Picker:** Filters the data globally by created\_at.  
* **Footer:** Version info and "Last Sync" timestamp.

### **2.2. The Three Views**

#### **View 1: Overview Page (Strategic)**

* **Top Row (KPI Cards):** \* Use st.metric with delta\_color="normal".  
  * *Total Open*, *Velocity (Closed/Week)*, *Bug Ratio*.  
* **Middle Row (Burn-up):** \* Full-width Plotly Line Chart.  
  * **Styling:** Minimalist mode. Remove grid lines on X-axis.  
* **Bottom Row (Distribution):** \* Two columns: *Work Distribution (Bar)* and *Status Split (Donut)*.

#### **View 2: Aging Page (Operational)**

* **Alert Banner:** If stale issues \> threshold, show st.warning("⚠️ High volume of stale issues detected").  
* **Chart:** Boxplots showing distribution of age\_days by Priority/Type.  
  * *UX:* Hovering over outlier dots must show the specific Issue Title and Assignee.

#### **View 3: Hygiene Page (Quality)**

* **Scorecard:** Large Radial Gauge (0-100%) showing overall data quality.  
* **Action Table:** A data grid (st.dataframe) showing invalid issues.  
  * *Highlighting:* Use pandas.style to color-code the error\_code column (Red background for critical errors).

#### **View 4: Release Management**

* **KPIs:** Progress %, Days Remaining, Scope (Total Issues).
* **Charts:** Burn-up Chart (Scope vs Completed over time).
* **Scope Table:** List of issues in the milestone, sorted by status.

#### **View 5: Value Stream (Flow)**

* **Charts:** Throughput (Bar), Cycle Time Scatter.
* **Drill-down:** Hierarchical grid showing parent-child relationships.

### **2.3. Hierarchical Data Grids**

Grids displaying Task/Subtask relationships (e.g., in Release or Flow views) must use **Visual Indentation** to represent topology:

* **Sorting:** Parents appear immediately before their children.
* **Indentation:** Child titles are prefixed with `↳ ` and indented.
* **Linking:** Clicking either Parent or Child ID opens the specific Work Item URL.

## **3\. State & Performance**

### **3.1. Caching Strategy**

* **Function:** load\_data()  
* **Implementation:** @st.cache\_data(ttl=900)  
* **Logic:** The data is loaded from Parquet into memory once every 15 minutes. All filtering (by team, by date) is then performed on the in-memory DataFrame for instant UI responsiveness.

## **4\. Visualization Logic**

### **4.1. Plotly Configuration**

All charts must use the Streamlit theme integration for backgrounds but override specific data colors.

* **Config Object:** config={'displayModeBar': False} (Hides the Plotly toolbar for a cleaner look).  
* **Layout Defaults:**  
  * margin=dict(l=0, r=0, t=30, b=0) (Tight layout).  
  * font=dict(family="Inter, sans-serif").  
* **Dark/Light Adaptability:**  
  * Do **not** set a fixed paper\_bgcolor. Use rgba(0,0,0,0) to let the Streamlit theme shine through.  
  * Use the Semantic Palette defined in Section 1.2 for all data traces.

## **5\. Architecture Decision Records (ADR)**

### **5.1. Why Streamlit?**

* **Python Synergy:** Since the data pipeline (L1/L2) is already in Python/Pandas, Streamlit allows us to build the UI in the same language, sharing data models and logic without needing a complex REST/JSON bridge to a JavaScript frontend.

### **5.2. Why Plotly over Altair?**

* **Interactivity:** Plotly provides a more robust out-of-the-box toolset for zooming and panning, which is essential when analyzing a timeline containing thousands of issue "dots."

### **5.3. Why Semantic Color Mapping?**

* **Cognitive Load:** By rigidly defining "Bug \= Red" and "Feature \= Blue", users instantly recognize patterns across different charts without re-reading legends. This mapping must persist regardless of whether the user is in Dark or Light mode.

### **5.4. Why Custom CSS Injection for Cards?**

* **Decision:** Use **Custom CSS Injection** (`st.markdown`) via a wrapper function.
* **Why:** Streamlit's native `st.metric` does not support background colors, borders, or shadows. To achieve the "Bento Grid" look required for the **GitLabInsight** UI, we must inject a scoped CSS class. This trades a bit of purity for significantly better UX.

## **6\. Bento Grid Design System**

### **6.1. Metric Card Specification**
To achieve the "Modern SaaS" aesthetic, metrics are not flat text but encapsulated in **Cards**.

* **Class Name:** `.metric-card` (or targeted via `div[data-testid="stMetric"]`)
* **Properties:**
  * **Background:** Semantic (White for Light, Dark Grey for Dark).
  * **Border Radius:** `10px` to `12px` (Modern standard).
  * **Padding:** `15px 20px`.
  * **Shadow:** `0 2px 4px rgba(0,0,0,0.05)` (Subtle elevation).
  * **Border:** `1px solid #F0F2F6` (Light grey for definition).
  * **Hover Effect:** `transform: translateY(-2px)` and increased shadow for interactivity.

### **6.2. Implementation Strategy**
A helper function `style_metric_cards()` in `app/dashboard/components.py` will inject the necessary `<style>` block. This function must be called at the beginning of any view rendering KPI cards.

## **7. Adaptive Dark/Light Mode Support**

### **7.1. Architecture Decision: CSS Variables**
* **Decision:** Use **Streamlit Native CSS Variables** (e.g., `var(--secondary-background-color)`) for all custom styling.
* **Why:** Hardcoding Hex values (e.g., `#FFFFFF`) breaks Dark Mode. Using variables ensures that custom components inherit the correct background, text, and border colors automatically when the theme switches.

### **7.2. Implementation Guidelines**
1.  **Card Variables:**
    *   Background: `var(--secondary-background-color)`
    *   Text: `var(--text-color)`
    *   Border: `rgba(128, 128, 128, 0.2)` (Adaptive transparency)
2.  **Chart Transparency:**
    *   `paper_bgcolor='rgba(0,0,0,0)'`
    *   `plot_bgcolor='rgba(0,0,0,0)'`
    *   `yaxis=dict(gridcolor='rgba(128, 128, 128, 0.2)')`
