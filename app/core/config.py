from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
from pydantic import field_validator
import os

class Settings(BaseSettings):
    # API Configuration
    API_V1_STR: str = "/api/v1"  # URL prefix for API version 1 endpoints (e.g., /api/v1/videos)
    
    # JWT Configuration
    JWT_SECRET_KEY: str = "your-secret-key"  # Change in production
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 3000
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Database Configuration
    SUPABASE_URL: str
    SUPABASE_KEY: str
    
    # Supabase Storage Configuration
    SUPABASE_STORAGE_URL: str  # Full Supabase storage URL (e.g., https://xxx.supabase.co/storage/v1)
    SUPABASE_S3_ENDPOINT: str
    SUPABASE_S3_ACCESS_KEY_ID: str
    SUPABASE_S3_SECRET_ACCESS_KEY: str
    SUPABASE_S3_REGION: str = "eu-central-1"  # Default region for Supabase storage
    
    # OpenAI Configuration
    OPENAI_API_KEY: str
    
    # Storage Configuration
    STORAGE_BUCKET: str = "videos"  # This should match your bucket name in Supabase
    MAX_VIDEO_SIZE: int = 20 * 1024 * 1024  # 20MB
    ALLOWED_VIDEO_TYPES: set = {
        "video/mp4",
        "video/webm",
        "audio/wav"
    }
    
    # Whisper API Configuration
    WHISPER_COST_PER_MINUTE: float = 0.006  # Cost in USD per minute
    MAX_VIDEO_DURATION_MINUTES: int = 60  # Maximum allowed video duration
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        env_file_encoding='utf-8',
        extra='allow'
    )

settings = Settings() 