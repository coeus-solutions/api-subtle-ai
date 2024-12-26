from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
from pydantic import field_validator

class Settings(BaseSettings):
    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Video Analyzer API"
    
    # JWT Configuration
    JWT_SECRET_KEY: str = "your-secret-key"  # Change in production
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Database Configuration
    SUPABASE_URL: str
    SUPABASE_KEY: str
    
    # Supabase Storage Configuration
    SUPABASE_STORAGE_URL: str
    SUPABASE_S3_ACCESS_KEY_ID: str
    SUPABASE_S3_SECRET_ACCESS_KEY: str
    SUPABASE_S3_REGION: str
    
    # OpenAI Configuration
    OPENAI_API_KEY: str
    
    # Storage Configuration
    STORAGE_BUCKET: str = "videos"
    MAX_VIDEO_SIZE: int = 100 * 1024 * 1024  # 100MB
    ALLOWED_VIDEO_TYPES: List[str] = ["video/mp4", "video/avi", "video/quicktime"]
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        env_file_encoding='utf-8',
        extra='allow'
    )

settings = Settings() 