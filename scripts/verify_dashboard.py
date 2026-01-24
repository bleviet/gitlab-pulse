import sys
import os
import logging

# Config logging before imports
# Force Streamlit to be quiet via Env Var if it checks it
os.environ["STREAMLIT_LOG_LEVEL"] = "error"

# Add project root to path
sys.path.append(os.getcwd())

# Aggressively silence Streamlit loggers
loggers = [
    "streamlit",
    "streamlit.runtime.caching",
    "streamlit.runtime.caching.cache_data_api",
    "streamlit.runtime.caching.cache_resource_api",
]
for name in loggers:
    logging.getLogger(name).setLevel(logging.CRITICAL)
    logging.getLogger(name).disabled = True

print("Verifying dashboard imports...")

try:
    from app.dashboard.widgets import kpis, charts, tables, features
    print("✅ Widgets modules imported")

    # Verify specific attributes
    print("Checking widget attributes...")
    _ = charts.milestone_timeline
    _ = charts.milestone_burnup
    _ = tables.issue_detail_grid
    _ = features.ai_assistant
    print("✅ Widget attributes verified")

    from app.dashboard.views import capacity, release, hygiene, overview, stats, aging, admin
    print("✅ Views imported")

    print("\nAll modules loaded successfully.")

except AttributeError as e:
    print(f"\n❌ AttributeError: {e}")
    sys.exit(1)
except ImportError as e:
    print(f"\n❌ ImportError: {e}")
    sys.exit(1)
except Exception as e:
    print(f"\n❌ Error: {e}")
    sys.exit(1)
