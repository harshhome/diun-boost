from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.dashboard_snapshot import load_dashboard_json

APP_NAME = os.getenv("DIUN_DASHBOARD_APP_NAME", "DIUN Dashboard")
DASHBOARD_JSON_PATH = Path(os.getenv("DIUN_DASHBOARD_JSON_PATH", "/config/dashboard.json"))

app = FastAPI(title=APP_NAME)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


class DashboardLoadError(RuntimeError):
    pass


def read_dashboard_snapshot() -> dict[str, object]:
    try:
        return load_dashboard_json(DASHBOARD_JSON_PATH)
    except FileNotFoundError as exc:
        raise DashboardLoadError(f"Dashboard snapshot not found: {DASHBOARD_JSON_PATH}") from exc
    except Exception as exc:  # pragma: no cover - defensive runtime guard
        raise DashboardLoadError(str(exc)) from exc


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    try:
        dashboard = read_dashboard_snapshot()
        return templates.TemplateResponse(
            request,
            "index.html",
            {"app_name": APP_NAME, "dashboard": dashboard, "error": None},
        )
    except DashboardLoadError as exc:
        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "app_name": APP_NAME,
                "dashboard": None,
                "error": {"message": "Unable to load pending updates", "details": str(exc)},
            },
            status_code=502,
        )


@app.get("/healthz")
def healthz() -> JSONResponse:
    return JSONResponse({"status": "ok", "app": APP_NAME})


@app.get("/api/report")
def api_report() -> JSONResponse:
    try:
        return JSONResponse(read_dashboard_snapshot())
    except DashboardLoadError as exc:
        return JSONResponse(
            {"message": "Unable to load pending updates", "details": str(exc)},
            status_code=502,
        )
