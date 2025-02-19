from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
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

@app.get("/", include_in_schema=False)
async def root():
    """Redirect root path to API documentation."""
    return RedirectResponse("/docs")

@app.get("/health", include_in_schema=False, status_code=status.HTTP_200_OK)
async def health_check():
    """Health check endpoint for monitoring service status."""
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": "healthy"}
    ) 