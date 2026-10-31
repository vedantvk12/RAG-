from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from app.api.v1.api import api_router
from app.db.qdrant import init_qdrant

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize Qdrant
    await init_qdrant()
    
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Enterprise Knowledge & Decision Intelligence Platform API",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to frontend domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

@app.get("/health")
async def health_check():
    return {"status": "ok", "environment": settings.ENVIRONMENT}
