"""FastAPI application factory serving the dashboard API and built React SPA."""

from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.dashboard.admin import create_admin_router
from app.dashboard.schemas import DashboardPayload, HealthResponse
from app.dashboard.service import DashboardService

load_dotenv()

_DEFAULT_FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


def create_app(
    service: DashboardService | None = None,
    frontend_dist: Path | None = None,
) -> FastAPI:
    """Create the FastAPI application with API routes and SPA static serving."""
    dashboard_service = service or DashboardService()
    dist_dir = frontend_dist if frontend_dist is not None else _DEFAULT_FRONTEND_DIST

    application = FastAPI(title="GitLab Pulse API", version="0.1.0")
    application.add_middleware(GZipMiddleware, minimum_size=1000)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.get("/api/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok")

    @application.get("/api/dashboard", response_model=DashboardPayload)
    def get_dashboard() -> DashboardPayload:
        return dashboard_service.get_dashboard_payload()

    application.include_router(create_admin_router(dashboard_service))

    index_file = dist_dir / "index.html"
    if index_file.exists():
        assets_dir = dist_dir / "assets"
        if assets_dir.exists():
            application.mount(
                "/assets", StaticFiles(directory=assets_dir), name="frontend-assets"
            )
        static_dir = dist_dir / "static"
        if static_dir.exists():
            application.mount(
                "/static", StaticFiles(directory=static_dir), name="frontend-static"
            )

        @application.get("/", include_in_schema=False)
        def serve_root() -> FileResponse:
            return FileResponse(index_file)

        @application.get("/{full_path:path}", include_in_schema=False)
        def serve_spa_fallback(full_path: str) -> FileResponse:
            if full_path.startswith("api/") or full_path == "api":
                raise HTTPException(status_code=404, detail="API endpoint not found")
            candidate = (dist_dir / full_path).resolve()
            try:
                candidate.relative_to(dist_dir.resolve())
            except ValueError as exc:
                raise HTTPException(status_code=404, detail="Not found") from exc
            if candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(index_file)
    else:

        @application.get("/", include_in_schema=False)
        def serve_dev_notice() -> JSONResponse:
            return JSONResponse(
                status_code=200,
                content={
                    "message": "Frontend build not found. Run 'cd frontend && npm run build' or start Vite dev server ('cd frontend && npm run dev').",
                    "api": "/api/dashboard",
                },
            )

    return application


app = create_app()
