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


def create_admin_router(service: DashboardService) -> APIRouter:
    """Build the admin router with an isolated in-memory session token store."""
    router = APIRouter(prefix="/api/admin", tags=["admin"])
    valid_tokens: set[str] = set()

    def _require_admin(session_token: str | None) -> None:
        if not session_token or session_token not in valid_tokens:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Admin authentication required.",
            )

    @router.get("/status", response_model=AdminStatusResponse)
    def admin_status(
        pulse_admin_session: str | None = Cookie(default=None, alias=ADMIN_COOKIE_NAME),
    ) -> AdminStatusResponse:
        is_valid = bool(pulse_admin_session and pulse_admin_session in valid_tokens)
        return AdminStatusResponse(authenticated=is_valid)

    @router.post("/login", response_model=AdminStatusResponse)
    def admin_login(payload: AdminLoginRequest, response: Response) -> AdminStatusResponse:
        expected = _expected_admin_password()
        if not hmac.compare_digest(payload.password, expected):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid admin password.",
            )
        token = secrets.token_urlsafe(32)
        valid_tokens.add(token)
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
            valid_tokens.discard(pulse_admin_session)
        response.delete_cookie(key=ADMIN_COOKIE_NAME, path="/")
        return AdminStatusResponse(authenticated=False)

    @router.post("/run/collector", response_model=AdminJobResponse)
    async def run_collector(
        pulse_admin_session: str | None = Cookie(default=None, alias=ADMIN_COOKIE_NAME),
    ) -> AdminJobResponse:
        _require_admin(pulse_admin_session)
        job = await _run_script("app/collector/orchestrator.py", "Collector (L1)")
        if job.success:
            service.clear_cache()
        return job

    @router.post("/run/processor", response_model=AdminJobResponse)
    async def run_processor(
        pulse_admin_session: str | None = Cookie(default=None, alias=ADMIN_COOKIE_NAME),
    ) -> AdminJobResponse:
        _require_admin(pulse_admin_session)
        job = await _run_script("app/processor/main.py", "Processor (L2)")
        if job.success:
            service.clear_cache()
        return job

    @router.post("/clear-cache", response_model=dict[str, bool])
    def clear_cache(
        pulse_admin_session: str | None = Cookie(default=None, alias=ADMIN_COOKIE_NAME),
    ) -> dict[str, bool]:
        _require_admin(pulse_admin_session)
        service.clear_cache()
        return {"ok": True}

    return router
