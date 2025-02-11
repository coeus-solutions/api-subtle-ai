from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, videos, subtitles, users
from app.core.config import settings

app = FastAPI(
    title="SubtleAI API",
    description="Backend API for AI-powered video subtitle generation and management",
    version="1.0.0"
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(videos.router, prefix="/api/v1/videos", tags=["Videos"])
app.include_router(subtitles.router, prefix="/api/v1/subtitles", tags=["Subtitles"])
app.include_router(users.router, prefix="/api/v1", tags=["Users"])

@app.get("/")
async def root():
    return {"message": "Welcome to SubtleAI API"} 