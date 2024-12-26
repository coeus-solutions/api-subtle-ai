from datetime import datetime
from uuid import UUID, uuid4
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, HttpUrl

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
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

class Video(BaseModelWithTimestamps):
    id: Optional[int] = None
    uuid: UUID = Field(default_factory=uuid4)
    user_id: int
    video_url: str
    status: Optional[str] = "queued"
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

class Subtitle(BaseModelWithTimestamps):
    id: Optional[int] = None
    uuid: UUID = Field(default_factory=uuid4)
    video_id: int
    subtitle_url: str
    format: Optional[str] = "srt"
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

class Log(BaseModelWithTimestamps):
    id: Optional[int] = None
    uuid: UUID = Field(default_factory=uuid4)
    user_id: int
    action: str
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

# Request Models
class UserCreate(BaseModel):
    email: EmailStr
    password: str

# Response Models
class MessageResponse(BaseModel):
    message: str
    detail: Optional[str] = None

class UserResponse(BaseModel):
    email: EmailStr
    created_at: Optional[datetime] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
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
    subtitle_url: str
    format: Optional[str] = "srt"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class ListSubtitlesResponse(BaseModel):
    message: str
    count: int
    subtitles: List[SubtitleResponse]

class VideoUploadResponse(BaseModel):
    message: str
    video_uuid: str
    file_url: str
    status: Optional[str] = "queued"
    detail: Optional[str] = None

class SubtitleGenerationResponse(BaseModel):
    message: str
    video_uuid: str
    subtitle_uuid: str
    subtitle_url: str
    status: Optional[str] = "completed"
    detail: Optional[str] = None

class VideoDeleteResponse(BaseModel):
    message: str
    video_uuid: str
    detail: Optional[str] = None

class ErrorResponse(BaseModel):
    detail: str 

class VideoResponse(BaseModel):
    uuid: str
    video_url: str
    status: Optional[str] = "queued"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class VideoListResponse(BaseModel):
    message: str
    count: int
    videos: List[VideoResponse]
    detail: Optional[str] = None 