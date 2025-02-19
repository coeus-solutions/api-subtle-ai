from datetime import datetime
from uuid import UUID, uuid4
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, HttpUrl, validator
from decimal import Decimal
from enum import Enum

def round_decimal(value: float) -> float:
    """Round float to 2 decimal places"""
    return round(float(value), 2)

class SupportedLanguage(str, Enum):
    """Supported languages for subtitle generation and dubbing"""
    ENGLISH = "en"
    GERMAN = "de"
    SPANISH = "es"
    FRENCH = "fr"
    JAPANESE = "ja"
    RUSSIAN = "ru"
    ITALIAN = "it"
    CHINESE = "zh"
    TURKISH = "tr"
    KOREAN = "ko"
    PORTUGUESE = "pt"

    @classmethod
    def get_language_name(cls, code: str) -> str:
        """Get full language name from code"""
        names = {
            "en": "English",
            "de": "German",
            "es": "Spanish",
            "fr": "French",
            "ja": "Japanese",
            "ru": "Russian",
            "it": "Italian",
            "zh": "Chinese",
            "tr": "Turkish",
            "ko": "Korean",
            "pt": "Portuguese"
        }
        return names.get(code, code)

class BaseModelWithTimestamps(BaseModel):
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        arbitrary_types_allowed = True

class User(BaseModelWithTimestamps):
    id: Optional[int] = None
    uuid: UUID = Field(default_factory=uuid4)
    email: EmailStr
    password_hash: str
    minutes_consumed: float = Field(default=0)
    free_minutes_used: float = Field(default=0)
    total_cost: float = Field(default=0)
    allowed_minutes: float = Field(default=30.0)  # Default to 30 minutes
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

    _round_minutes_consumed = validator('minutes_consumed', allow_reuse=True)(round_decimal)
    _round_free_minutes_used = validator('free_minutes_used', allow_reuse=True)(round_decimal)
    _round_total_cost = validator('total_cost', allow_reuse=True)(round_decimal)
    _round_allowed_minutes = validator('allowed_minutes', allow_reuse=True)(round_decimal)

class Video(BaseModelWithTimestamps):
    id: Optional[int] = None
    uuid: UUID = Field(default_factory=uuid4)
    user_id: int
    video_url: str
    original_name: Optional[str] = None
    duration_minutes: float = Field(default=0)
    status: Optional[str] = "queued"
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

    _round_duration = validator('duration_minutes', allow_reuse=True)(round_decimal)

class Subtitle(BaseModelWithTimestamps):
    id: Optional[int] = None
    uuid: UUID = Field(default_factory=uuid4)
    video_id: int
    subtitle_url: str
    format: Optional[str] = "srt"
    language: SupportedLanguage = Field(default=SupportedLanguage.ENGLISH)
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

# Request Models
class UserCreate(BaseModel):
    email: EmailStr
    password: str

class VideoUploadRequest(BaseModel):
    """Request model for video upload endpoint."""
    language: SupportedLanguage = Field(
        default=SupportedLanguage.ENGLISH,
        description="Target language for subtitle generation"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "language": "en"
            }
        }

# Response Models
class MessageResponse(BaseModel):
    message: str
    detail: Optional[str] = None

class UserResponse(BaseModel):
    email: EmailStr
    minutes_consumed: float = Field(default=0)
    free_minutes_used: float = Field(default=0)
    total_cost: float = Field(default=0)
    minutes_remaining: float = Field(default=0)  # Calculated field
    created_at: Optional[datetime] = None

    _round_minutes_consumed = validator('minutes_consumed', allow_reuse=True)(round_decimal)
    _round_free_minutes_used = validator('free_minutes_used', allow_reuse=True)(round_decimal)
    _round_total_cost = validator('total_cost', allow_reuse=True)(round_decimal)
    _round_minutes_remaining = validator('minutes_remaining', allow_reuse=True)(round_decimal)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class UserDetailsResponse(BaseModel):
    """Detailed user information including usage statistics"""
    email: EmailStr
    minutes_consumed: float = Field(default=0)
    free_minutes_used: float = Field(default=0)
    total_cost: float = Field(default=0)
    minutes_remaining: float = Field(default=0)
    cost_per_minute: float = Field(default=0.10)
    free_minutes_allocation: float = Field(default=30.0)  # Changed from 50.0 to 30.0
    allowed_minutes: float = Field(default=30.0)  # Add allowed minutes field
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    _round_minutes_consumed = validator('minutes_consumed', allow_reuse=True)(round_decimal)
    _round_free_minutes_used = validator('free_minutes_used', allow_reuse=True)(round_decimal)
    _round_total_cost = validator('total_cost', allow_reuse=True)(round_decimal)
    _round_minutes_remaining = validator('minutes_remaining', allow_reuse=True)(round_decimal)
    _round_cost_per_minute = validator('cost_per_minute', allow_reuse=True)(round_decimal)
    _round_free_minutes_allocation = validator('free_minutes_allocation', allow_reuse=True)(round_decimal)
    _round_allowed_minutes = validator('allowed_minutes', allow_reuse=True)(round_decimal)

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "minutes_consumed": 75.50,
                "free_minutes_used": 30.00,
                "total_cost": 4.55,  # (75.5 - 30.0) * $0.10
                "minutes_remaining": 0.00,
                "cost_per_minute": 0.10,
                "free_minutes_allocation": 30.00,
                "allowed_minutes": 30.00,
                "created_at": "2024-01-29T12:00:00Z",
                "updated_at": "2024-01-29T12:00:00Z"
            }
        }

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class RegisterResponse(BaseModel):
    message: str
    user: Optional[UserResponse] = None

class SubtitleResponse(BaseModel):
    uuid: str
    video_uuid: str
    video_original_name: Optional[str] = None
    subtitle_url: str
    format: Optional[str] = "srt"
    language: SupportedLanguage = Field(default=SupportedLanguage.ENGLISH)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class ListSubtitlesResponse(BaseModel):
    message: str
    count: int
    subtitles: List[SubtitleResponse]

class VideoUploadResponse(BaseModel):
    """Response model for video upload endpoint."""
    message: str
    video_uuid: str
    file_url: str
    original_name: str
    status: Optional[str] = "queued"
    duration_minutes: Optional[float] = Field(default=None)
    estimated_cost: Optional[float] = Field(default=None)
    detail: Optional[str] = None
    language: SupportedLanguage = Field(default=SupportedLanguage.ENGLISH)

    _round_duration = validator('duration_minutes', pre=True, allow_reuse=True)(lambda v: round_decimal(v) if v is not None else None)
    _round_cost = validator('estimated_cost', pre=True, allow_reuse=True)(lambda v: round_decimal(v) if v is not None else None)

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Video uploaded successfully",
                "video_uuid": "123e4567-e89b-12d3-a456-426614174000",
                "file_url": "https://example.com/storage/videos/video.mp4",
                "original_name": "my_video.mp4",
                "status": "queued",
                "duration_minutes": 5.50,
                "estimated_cost": 0.55,
                "detail": "Estimated processing cost: $0.55 for 5.50 minutes",
                "language": "en"
            }
        }

class SubtitleGenerationRequest(BaseModel):
    """Request model for subtitle generation endpoint."""
    enable_dubbing: bool = Field(
        default=False,
        description="Whether to enable video dubbing using ElevenLabs"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "enable_dubbing": True  # Example: Enable dubbing with video's saved language
            }
        }

class DubbingStatusResponse(BaseModel):
    """Response model for checking dubbing status."""
    message: str
    video_uuid: str
    dubbing_id: str
    language: SupportedLanguage = Field(default=SupportedLanguage.ENGLISH)
    status: str = Field(
        description="ElevenLabs dubbing status: 'dubbing' (in progress), 'dubbed' (completed), or 'failed'"
    )
    duration_minutes: Optional[float] = Field(default=None)
    detail: Optional[str] = None
    expected_duration_sec: Optional[float] = Field(default=None)

    _round_duration = validator('duration_minutes', pre=True, allow_reuse=True)(lambda v: round_decimal(v) if v is not None else None)
    _round_expected_duration = validator('expected_duration_sec', pre=True, allow_reuse=True)(lambda v: round_decimal(v) if v is not None else None)

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Dubbing status: dubbing",
                "video_uuid": "123e4567-e89b-12d3-a456-426614174000",
                "dubbing_id": "dub_123456789",
                "language": "es",
                "status": "dubbing",  # ElevenLabs status
                "duration_minutes": 5.50,
                "detail": "Current status from ElevenLabs: dubbing",
                "expected_duration_sec": 330.0
            }
        }

class DubbingResponse(BaseModel):
    """Response model for getting dubbed video."""
    message: str
    video_uuid: str
    dubbing_id: str
    dubbed_video_url: str
    language: SupportedLanguage = Field(default=SupportedLanguage.ENGLISH)
    status: str = Field(
        default="dubbed",
        description="ElevenLabs dubbing status: will always be 'dubbed' for successful responses"
    )
    duration_minutes: Optional[float] = Field(default=None)
    processing_cost: Optional[float] = Field(default=None)
    detail: Optional[str] = None

    _round_duration = validator('duration_minutes', pre=True, allow_reuse=True)(lambda v: round_decimal(v) if v is not None else None)
    _round_cost = validator('processing_cost', pre=True, allow_reuse=True)(lambda v: round_decimal(v) if v is not None else None)

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Dubbed video ready",
                "video_uuid": "123e4567-e89b-12d3-a456-426614174000",
                "dubbing_id": "dub_123456789",
                "dubbed_video_url": "https://example.com/storage/dubbed_videos/video.mp4",
                "language": "es",
                "status": "dubbed",  # ElevenLabs status
                "duration_minutes": 5.50,
                "processing_cost": 0.55,
                "detail": "Successfully retrieved dubbed video"
            }
        }

class SubtitleGenerationResponse(BaseModel):
    """Response model for subtitle generation endpoint."""
    message: str
    video_uuid: str
    subtitle_uuid: Optional[str] = None
    subtitle_url: Optional[str] = None
    processed_video_url: Optional[str] = None  # URL of video with burned subtitles
    dubbing_id: Optional[str] = None  # Added for dubbing support
    dubbed_video_url: Optional[str] = None  # Added for dubbing support
    language: SupportedLanguage = Field(default=SupportedLanguage.ENGLISH)
    status: str = "completed"
    duration_minutes: Optional[float] = Field(default=None)
    processing_cost: Optional[float] = Field(default=None)
    detail: Optional[str] = None
    expected_duration_sec: Optional[float] = Field(default=None)  # Added for dubbing support

    _round_duration = validator('duration_minutes', pre=True, allow_reuse=True)(lambda v: round_decimal(v) if v is not None else None)
    _round_cost = validator('processing_cost', pre=True, allow_reuse=True)(lambda v: round_decimal(v) if v is not None else None)
    _round_expected_duration = validator('expected_duration_sec', pre=True, allow_reuse=True)(lambda v: round_decimal(v) if v is not None else None)

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Subtitles generated successfully",
                "video_uuid": "123e4567-e89b-12d3-a456-426614174000",
                "subtitle_uuid": "987fcdeb-89ab-12d3-a456-426614174000",
                "subtitle_url": "https://example.com/storage/subtitles/subtitle.srt",
                "processed_video_url": "https://example.com/storage/processed_videos/video_with_subtitles.mp4",  # Added example
                "dubbing_id": "dub_123456789",  # Only present if dubbing enabled
                "dubbed_video_url": "https://example.com/storage/dubbed_videos/video.mp4",  # Only present if dubbing enabled
                "language": "es",
                "status": "completed",
                "duration_minutes": 5.50,
                "processing_cost": 0.55,
                "detail": "Successfully generated Spanish subtitles and processed video. Cost: $0.55",
                "expected_duration_sec": 330.0  # Only present if dubbing enabled
            }
        }

class VideoDeleteResponse(BaseModel):
    message: str
    video_uuid: str
    detail: Optional[str] = None

class ErrorResponse(BaseModel):
    detail: str 

class VideoSubtitleInfo(BaseModel):
    uuid: str
    language: SupportedLanguage
    subtitle_url: str
    created_at: Optional[datetime] = None

class VideoResponse(BaseModel):
    uuid: str
    video_url: str
    original_name: Optional[str] = None
    duration_minutes: float = Field(default=0)
    status: Optional[str] = "queued"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    has_subtitles: bool = False
    subtitle_languages: List[str] = []
    subtitles: Optional[List[VideoSubtitleInfo]] = None
    dubbed_video_url: Optional[str] = None
    burned_video_url: Optional[str] = None  # URL of video with burned subtitles
    dubbing_id: Optional[str] = None
    is_dubbed_audio: bool = Field(default=False)

    _round_duration = validator('duration_minutes', allow_reuse=True)(round_decimal)

class VideoListResponse(BaseModel):
    message: str
    count: int
    videos: List[VideoResponse]
    detail: Optional[str] = None 

class SubtitleBurningRequest(BaseModel):
    """Request model for burning subtitles into video."""
    subtitle_uuid: str = Field(
        description="UUID of the subtitle file to burn into the video"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "subtitle_uuid": "987fcdeb-89ab-12d3-a456-426614174000"
            }
        }

class SubtitleBurningResponse(BaseModel):
    """Response model for subtitle burning endpoint."""
    message: str
    video_uuid: str
    subtitle_uuid: str
    burned_video_url: str
    language: SupportedLanguage = Field(default=SupportedLanguage.ENGLISH)
    status: str = "completed"
    detail: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Subtitles burned successfully",
                "video_uuid": "123e4567-e89b-12d3-a456-426614174000",
                "subtitle_uuid": "987fcdeb-89ab-12d3-a456-426614174000",
                "burned_video_url": "https://example.com/storage/processed_videos/video_with_subtitles.mp4",
                "language": "en",
                "status": "completed",
                "detail": "Successfully burned English subtitles into video"
            }
        } 
