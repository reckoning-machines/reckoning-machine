from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Reckoning Machine")


# -----------------------------
# Health + version
# -----------------------------
@app.get("/health")
def health():
    return {"status": "ok", "service": "reckoning-machine"}


@app.get("/version")
def version():
    return {"version": "0.1.0"}


# -----------------------------
# Optional: DB ping
# -----------------------------
@app.get("/db/ping")
def db_ping():
    try:
        from sqlalchemy import text
        from app.db.session import SessionLocal

        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
        finally:
            db.close()
        return {"db": "ok"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"db": "error", "detail": str(e)})


# -----------------------------
# API routers
# -----------------------------
from app.api.tasks import router as tasks_router
from app.api.manifests import router as manifests_router
from app.api.runs import router as runs_router

app.include_router(tasks_router, prefix="/api")
app.include_router(manifests_router, prefix="/api")
app.include_router(runs_router, prefix="/api")


# -----------------------------
# Static frontend mount (MUST be last)
# -----------------------------
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
