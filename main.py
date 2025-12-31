"""
WeOrder - Unified Order Management System
FastAPI Application Entry Point
"""
import uvicorn
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager
import os

from app.core import settings, engine, Base
from app.web.router import web_router
from app.api.router import api_router
from app.jobs import start_scheduler, stop_scheduler

# Lifespan for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create tables if not exist
    Base.metadata.create_all(bind=engine)
    print(f"WeOrder starting on port {settings.APP_PORT}")
    
    # Start background scheduler for order sync
    try:
        start_scheduler()
        print("Order sync scheduler started")
    except Exception as e:
        print(f"Warning: Could not start scheduler: {e}")
    
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

# Mount static files
static_path = os.path.join(os.path.dirname(__file__), "app", "static")
app.mount("/static", StaticFiles(directory=static_path), name="static")

# Setup templates
templates_path = os.path.join(os.path.dirname(__file__), "app", "templates")
templates = Jinja2Templates(directory=templates_path)

# Include routers
app.include_router(web_router)
app.include_router(api_router, prefix="/api")

# Root redirect to dashboard
@app.get("/")
async def root():
    return RedirectResponse(url="/dashboard")

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "app": settings.APP_NAME}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.APP_PORT,
        reload=settings.DEBUG
    )
