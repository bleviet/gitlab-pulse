"""Admin authentication and pipeline operation endpoints."""

import asyncio
import hmac
import os
import secrets
import subprocess
import sys

from fastapi import APIRouter, Cookie, HTTPException, Response, status

from app.dashboard.schemas import (
    AdminJobResponse,
    AdminLoginRequest,
    AdminStatusResponse,
)
from app.dashboard.service import DashboardService

ADMIN_COOKIE_NAME = "pulse_admin_session"


def _expected_admin_password() -> str:
    return os.environ.get("ADMIN_PASSWORD", "admin")


async def _run_script(script_path: str, step: str) -> AdminJobResponse:
    def _execute() -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            check=False,
        )

    result = await asyncio.to_thread(_execute)
    return AdminJobResponse(
        step=step,
        returncode=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
        success=result.returncode == 0,
    )


_pipeline_lock = asyncio.Lock()


async def run_pipeline_step(
    script_path: str, step: str, service: DashboardService
) -> AdminJobResponse:
    """Run a pipeline script exclusively and clear the dashboard cache on success.

    Args:
        script_path: Path of the Python script to run
        step: Human-readable step name reported in the response
        service: Dashboard service whose cache is cleared after a successful run

    Returns:
        The job result, including captured output
    """
    async with _pipeline_lock:
        job = await _run_script(script_path, step)
        if job.success:
            service.clear_cache()
        return job


class AdminSessions:
    """In-memory store of valid admin session tokens."""

    def __init__(self) -> None:
        """Create an empty session store."""
        self._tokens: set[str] = set()

    def issue(self) -> str:
        """Create and remember a new session token."""
        token = secrets.token_urlsafe(32)
        self._tokens.add(token)
        return token

    def revoke(self, token: str) -> None:
        """Forget a session token if it exists."""
        self._tokens.discard(token)

    def is_valid(self, token: str | None) -> bool:
        """Return whether the token belongs to an active session."""
        return bool(token and token in self._tokens)

    def require(self, token: str | None) -> None:
        """Raise HTTP 401 unless the token belongs to an active session."""
        if not self.is_valid(token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Admin authentication required.",
            )


def create_admin_router(service: DashboardService, sessions: AdminSessions) -> APIRouter:
    """Build the admin router backed by the shared session store."""
    router = APIRouter(prefix="/api/admin", tags=["admin"])

    @router.get("/status", response_model=AdminStatusResponse)
    def admin_status(
        pulse_admin_session: str | None = Cookie(default=None, alias=ADMIN_COOKIE_NAME),
    ) -> AdminStatusResponse:
        return AdminStatusResponse(authenticated=sessions.is_valid(pulse_admin_session))

    @router.post("/login", response_model=AdminStatusResponse)
    def admin_login(payload: AdminLoginRequest, response: Response) -> AdminStatusResponse:
        expected = _expected_admin_password()
        if not hmac.compare_digest(payload.password, expected):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid admin password.",
            )
        token = sessions.issue()
        response.set_cookie(
            key=ADMIN_COOKIE_NAME,
            value=token,
            httponly=True,
            samesite="lax",
            path="/",
        )
        return AdminStatusResponse(authenticated=True)

    @router.post("/logout", response_model=AdminStatusResponse)
    def admin_logout(
        response: Response,
        pulse_admin_session: str | None = Cookie(default=None, alias=ADMIN_COOKIE_NAME),
    ) -> AdminStatusResponse:
        if pulse_admin_session:
            sessions.revoke(pulse_admin_session)
        response.delete_cookie(key=ADMIN_COOKIE_NAME, path="/")
        return AdminStatusResponse(authenticated=False)

    @router.post("/run/collector", response_model=AdminJobResponse)
    async def run_collector(
        pulse_admin_session: str | None = Cookie(default=None, alias=ADMIN_COOKIE_NAME),
    ) -> AdminJobResponse:
        sessions.require(pulse_admin_session)
        return await run_pipeline_step(
            "app/collector/orchestrator.py", "Collector (L1)", service
        )

    @router.post("/run/processor", response_model=AdminJobResponse)
    async def run_processor(
        pulse_admin_session: str | None = Cookie(default=None, alias=ADMIN_COOKIE_NAME),
    ) -> AdminJobResponse:
        sessions.require(pulse_admin_session)
        return await run_pipeline_step(
            "app/processor/main.py", "Processor (L2)", service
        )

    @router.post("/clear-cache", response_model=dict[str, bool])
    def clear_cache(
        pulse_admin_session: str | None = Cookie(default=None, alias=ADMIN_COOKIE_NAME),
    ) -> dict[str, bool]:
        sessions.require(pulse_admin_session)
        service.clear_cache()
        return {"ok": True}

    return router
