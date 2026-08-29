"""
FastAPI Server — main entry point for the production post-mortem system.

Run with:
    python server.py
    # or: uvicorn server:app --reload --port 8000
"""

from __future__ import annotations

import os
import sys

# Ensure safe console output on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from api.incidents import router as incidents_router
from api.integrations import router as integrations_router
from api.webhooks import router as webhooks_router

import storage

# Initialize database
storage.init_db()

app = FastAPI(
    title="Prism — Incident Intelligence Platform",
    description="AI-powered incident forensics. Refracting production telemetry into clear, executive-ready reports.",
    version="2.0.0",
)

# CORS — allow dashboard and external webhook sources
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(incidents_router)
app.include_router(integrations_router)
app.include_router(webhooks_router)

# Serve static dashboard files
DASHBOARD_DIR = os.path.join(os.path.dirname(__file__), "dashboard")
if os.path.exists(DASHBOARD_DIR):
    app.mount("/static", StaticFiles(directory=DASHBOARD_DIR), name="static")


@app.get("/")
async def serve_dashboard():
    """Serve the main dashboard page."""
    index_path = os.path.join(DASHBOARD_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "message": "Incident Post-Mortem Generator API",
        "docs": "/docs",
        "dashboard": "Dashboard files not found. Place index.html in /dashboard/",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "2.0.0"}


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    print(f"\n{'='*60}")
    print(f"  Prism v2.0 — Incident Intelligence Platform")
    print(f"  Dashboard:  http://localhost:{port}")
    print(f"  API Docs:   http://localhost:{port}/docs")
    print(f"  Webhooks:   http://localhost:{port}/webhooks/pagerduty")
    print(f"{'='*60}\n")

    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
