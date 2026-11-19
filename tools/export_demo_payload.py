"""Export the dashboard payload as a static JSON snapshot for the demo build."""

import argparse
import os
from pathlib import Path

from app.dashboard.service import DashboardService


def export_payload(service: DashboardService, output: Path) -> Path:
    """Write the dashboard payload to ``output`` atomically.

    Args:
        service: Dashboard service whose payload is exported.
        output: Destination JSON file. Parent directories are created.

    Returns:
        The path that was written.
    """
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output.with_suffix(output.suffix + ".tmp")
    tmp_path.write_text(
        service.get_dashboard_payload().model_dump_json(), encoding="utf-8"
    )
    os.replace(tmp_path, output)
    return output


def main() -> None:
    """CLI entry point: export the payload built from the default data paths."""
    parser = argparse.ArgumentParser(
        description="Export the dashboard payload as static JSON"
    )
    parser.add_argument("--output", type=Path, required=True, help="Output JSON path")
    args = parser.parse_args()
    written = export_payload(DashboardService(), args.output)
    print(f"Wrote {written}")


if __name__ == "__main__":
    main()
