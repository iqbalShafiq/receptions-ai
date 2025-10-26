from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import init_db
from app.api import routes
from app.services.scheduler import start_scheduler, stop_scheduler

# Initialize database
init_db()

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    debug=settings.debug
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(routes.router)


@app.on_event("startup")
async def startup_event():
    """Start background scheduler on app startup"""
    start_scheduler()
    print("Receptionist AI started - Scheduler running")


@app.on_event("shutdown")
async def shutdown_event():
    """Stop background scheduler on app shutdown"""
    stop_scheduler()
    print("Receptionist AI stopped")


@app.get("/")
def read_root():
    return {
        "message": "Welcome to Receptionist AI",
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
