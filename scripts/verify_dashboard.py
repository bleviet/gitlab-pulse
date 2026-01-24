import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

print("Verifying dashboard imports...")

try:
    from app.dashboard.widgets import kpis, charts, tables, features
    print("✅ Widgets modules imported")

    # Verify specific attributes
    print("Checking widget attributes...")
    _ = charts.milestone_timeline
    _ = charts.milestone_burnup
    _ = tables.quality_action_table
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
