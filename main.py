"""
WeOrder - Unified Order Management System
FastAPI Application Entry Point
"""
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, FileResponse
from contextlib import asynccontextmanager
import os

from app.core import settings, engine, Base
from app.api.router import api_router
from app.jobs import start_scheduler, stop_scheduler

# Lifespan for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create tables if not exist
    Base.metadata.create_all(bind=engine)
    print(f"WeOrder starting on port {settings.APP_PORT}")
    
    # Scheduler is started separately via API or background job
    # Do NOT start scheduler here - it blocks uvicorn startup
    print("Scheduler disabled in lifespan - start via /api/sync/start if needed")
    
    yield
    
    # Shutdown
    try:
        stop_scheduler()
        print("Order sync scheduler stopped")
    except Exception:
        pass
    print("WeOrder shutting down")

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="Unified Order, Stock, Fulfillment & Profit System",
    version="1.0.0",
    lifespan=lifespan
)


# Include routers
app.include_router(api_router, prefix="/api")

# Mount React static files
frontend_dist = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")
else:
    print("Warning: frontend/dist not found. Run 'npm run build' in frontend directory")

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "app": settings.APP_NAME}

# TikTok Webhook at root /webhook (for legacy URL compatibility)
from fastapi import Depends, BackgroundTasks
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.webhooks import tiktok_webhook as tiktok_webhook_handler

@app.post("/webhook")
async def webhook_root(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Root /webhook endpoint - forwards to TikTok webhook handler"""
    return await tiktok_webhook_handler(request, background_tasks, db)

# SPA Catch-all
@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    if full_path.startswith("api"):
        return {"error": "API route not found"}
        
    # Serve index.html for any other route (Client-side routing)
    if os.path.exists(os.path.join(frontend_dist, "index.html")):
        return FileResponse(os.path.join(frontend_dist, "index.html"))
    return {"message": "Frontend not built"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.APP_PORT,
        reload=settings.DEBUG
    )
