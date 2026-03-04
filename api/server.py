"""FastAPI server — main application entry point."""

import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Ensure project root is on sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))
os.chdir(_PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(_PROJECT_ROOT / ".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import engine, schedule, content, targets, templates, rules, personas, analytics, history, alerts


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    yield


app = FastAPI(
    title="LinkedIn Dashboard API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow dashboard frontend
allowed_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all route modules under /api prefix
app.include_router(engine.router, prefix="/api")
app.include_router(schedule.router, prefix="/api")
app.include_router(content.router, prefix="/api")
app.include_router(targets.router, prefix="/api")
app.include_router(templates.router, prefix="/api")
app.include_router(rules.router, prefix="/api")
app.include_router(personas.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(history.router, prefix="/api")
app.include_router(alerts.router, prefix="/api")


@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "linkedin-dashboard-api"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.server:app",
        host="0.0.0.0",
        port=int(os.getenv("API_PORT", "8000")),
        reload=True,
    )
