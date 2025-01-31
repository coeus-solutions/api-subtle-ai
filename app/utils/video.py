import os
import tempfile
from moviepy.editor import VideoFileClip
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

def get_video_duration(file_path: str) -> float:
    """
    Get the duration of a video file in minutes.
    Returns -1 if duration cannot be determined.
    """
    try:
        with VideoFileClip(file_path) as video:
            return video.duration / 60.0  # Convert seconds to minutes
    except Exception as e:
        logger.error(f"Error getting video duration: {str(e)}")
        return -1

def estimate_whisper_cost(duration_minutes: float) -> float:
    """
    Estimate the cost of processing a video with Whisper API.
    """
    return duration_minutes * settings.WHISPER_COST_PER_MINUTE

def validate_video_duration(file_path: str) -> tuple[bool, float, float]:
    """
    Validate video duration and estimate processing cost.
    Returns (is_valid, duration_minutes, estimated_cost)
    """
    duration = get_video_duration(file_path)
    if duration <= 0:
        return False, 0, 0
        
    estimated_cost = estimate_whisper_cost(duration)
    is_valid = duration <= settings.MAX_VIDEO_DURATION_MINUTES
    
    return is_valid, duration, estimated_cost 