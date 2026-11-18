"""Module entry point to run the FastAPI dashboard server via Uvicorn."""

import argparse
import os

import uvicorn


def main() -> None:
    """Parse CLI arguments and launch the FastAPI server."""
    parser = argparse.ArgumentParser(description="Run the GitLab Pulse dashboard server.")
    parser.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    parser.add_argument(
        "--port", type=int, default=int(os.environ.get("PORT", "8501"))
    )
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    uvicorn.run(
        "app.dashboard.server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
