from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.core.db import init_db
from app.routers import auth, clients, tasks, admin, reports, regulatory, assistant, organizations, calendar, notifications
from app.services.scheduler import start_scheduler, shutdown_scheduler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize Beanie MongoDB connection
    logger.info("Initializing MongoDB connection...")
    await init_db()
    logger.info("MongoDB initialized successfully.")
    
    # Start APScheduler compliance checker job
    start_scheduler()
    
    yield
    
    # Shutdown: Stop scheduler
    shutdown_scheduler()

app = FastAPI(
    title="CS Compliance Dashboard API",
    description="Backend API for Registrar of Companies compliance workflow management.",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
configured_origins = [
    origin.strip()
    for origin in settings.FRONTEND_URL.split(",")
    if origin.strip()
]
origins = [
    "https://cs-compilance-dashboard-prlo.vercel.app",
    "http://localhost:5173",
    "http://localhost:3000",
]
if configured_origins:
    origins.extend(configured_origins)
else:
    origins = ["*"]

origins = list(dict.fromkeys(origins))

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(clients.router)
app.include_router(clients.clients_router)
app.include_router(tasks.router)
app.include_router(admin.router)
app.include_router(reports.router)
app.include_router(regulatory.router)
app.include_router(assistant.router)
app.include_router(organizations.router)
app.include_router(calendar.router)
app.include_router(notifications.router)

@app.get("/")
async def root():
    return {"status": "ok", "message": "CS Compliance Dashboard API is running."}
