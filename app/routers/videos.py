from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import JSONResponse
from typing import List
import os
import uuid
from datetime import datetime
import logging
import tempfile
from app.core.config import settings
from app.services.subtitle_service import subtitle_service
from app.utils.s3 import upload_file, delete_file, get_file_url, download_file
from app.utils.video import validate_video_duration
from app.utils.database import (
    save_video_metadata,
    get_video_by_uuid,
    update_video_status,
    delete_video_metadata,
    save_subtitle,
    get_user_videos,
    get_user_details,
    update_user_usage,
    get_user_subtitles
)
from app.routers.auth import get_current_user
from app.models.models import (
    VideoUploadResponse, 
    SubtitleGenerationResponse, 
    VideoDeleteResponse,
    VideoListResponse,
    VideoResponse,
    SubtitleGenerationRequest
)

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/upload", response_model=VideoUploadResponse, status_code=status.HTTP_200_OK)
async def upload_video(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload a video file for subtitle generation.
    
    - Validates video format and size
    - Checks video duration
    - Validates remaining free minutes
    - Maximum duration: 60 minutes
    - Cost: $0.10 per minute
    - First 50 minutes (worth $5.00) are free
    
    Returns:
        - Video UUID and URL
        - Video duration in minutes
        - Estimated processing cost
    """
    content = None
    file_path = None
    temp_file = None

    try:
        # Validate file exists
        if not file or not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No file provided"
            )
        
        # Read file content
        try:
            content = await file.read()
        except Exception as e:
            logger.error(f"Error reading file: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Error reading file"
            )
        
        # Validate file size
        if len(content) > settings.MAX_VIDEO_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File size exceeds maximum allowed size of 20MB. Your file size: {len(content) / (1024 * 1024):.2f}MB"
            )
        
        # Validate file type
        if file.content_type not in settings.ALLOWED_VIDEO_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type '{file.content_type}' not allowed. Allowed types: MP4, WebM, and WAV"
            )
        
        # Save to temporary file for duration validation
        try:
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1])
            temp_file.write(content)
            temp_file.close()
            
            # Validate duration and estimate cost
            is_valid, duration, estimated_cost = validate_video_duration(temp_file.name)
            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Video duration ({duration:.2f} minutes) exceeds maximum allowed duration of {settings.MAX_VIDEO_DURATION_MINUTES} minutes"
                )
            
            logger.info(f"Video duration: {duration:.2f} minutes, estimated cost: ${estimated_cost:.2f}")

            # Check user's remaining free minutes
            user_details = await get_user_details(current_user["id"])
            if not user_details:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User details not found"
                )
            
            minutes_remaining = user_details["minutes_remaining"]
            if minutes_remaining < duration and estimated_cost > 0:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail=f"Insufficient free minutes. You have {minutes_remaining:.2f} minutes remaining, but the video is {duration:.2f} minutes long. Please upgrade your account or use a shorter video."
                )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error validating video duration: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Error validating video duration"
            )
        
        # Generate unique filename and UUID
        try:
            file_extension = os.path.splitext(file.filename)[1]
            video_uuid = str(uuid.uuid4())
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = f"videos/{timestamp}_{video_uuid[:8]}{file_extension}"
        except Exception as e:
            logger.error(f"Error generating file path: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error generating file path"
            )
        
        # Upload to Supabase storage
        if not upload_file(file_path, content, file.content_type):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload video file"
            )
        
        # Generate public URL
        file_url = get_file_url(file_path)
        
        # Save video metadata to database
        try:
            video_data = {
                "uuid": video_uuid,
                "user_id": current_user["id"],
                "video_url": file_url,
                "original_name": file.filename,
                "duration_minutes": duration
            }            

            saved_video = await save_video_metadata(video_data)
            if not saved_video:
                # Clean up uploaded file if database save fails
                delete_file(file_path)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to save video metadata"
                )
        except Exception as e:
            # Clean up uploaded file if database save fails
            delete_file(file_path)
            logger.error(f"Error saving video metadata: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error saving video metadata: {str(e)}"
            )
        
        return VideoUploadResponse(
            message="Video uploaded successfully",
            video_uuid=video_uuid,
            file_url=file_url,
            original_name=file.filename,
            status="queued",
            duration_minutes=round(duration, 2),
            estimated_cost=round(estimated_cost, 2),
            detail=f"Estimated processing cost: ${estimated_cost:.2f} for {duration:.2f} minutes ({minutes_remaining:.2f} free minutes remaining)"
        )
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Unexpected error in upload_video: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )
    finally:
        # Clean up temporary files
        if temp_file and os.path.exists(temp_file.name):
            try:
                os.unlink(temp_file.name)
            except Exception as e:
                logger.error(f"Error cleaning up temporary file: {str(e)}")
        if content:
            del content

@router.post("/{video_uuid}/generate_subtitles", response_model=SubtitleGenerationResponse, status_code=status.HTTP_200_OK)
async def generate_subtitles(
    video_uuid: str,
    request: SubtitleGenerationRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Generate subtitles for a specific video.
    
    - Supports multiple languages through OpenAI's Whisper API
    - Cost: $0.10 per minute of video
    - First 50 minutes (worth $5.00) are free
    - Returns subtitle file in SRT format
    
    Parameters:
        - video_uuid: UUID of the uploaded video
        - language: Target language code (e.g., "en" for English, "es" for Spanish)
    
    Returns:
        - Subtitle UUID and URL
        - Processing status
        - Video duration and actual cost
    """
    try:
        # Validate UUID format
        try:
            uuid.UUID(video_uuid)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid video UUID format"
            )
        
        # Get video details from database
        video = await get_video_by_uuid(video_uuid)
        if not video:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video not found"
            )
        
        # Check if user owns the video
        if video["user_id"] != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to generate subtitles for this video"
            )
        
        # Check if video is in a valid state for subtitle generation
        if video["status"] not in ["queued", "uploaded", "failed"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot generate subtitles for video in '{video['status']}' status"
            )
        
        # Update video status to processing
        if not await update_video_status(video_uuid, "processing"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update video status to processing"
            )
        
        try:
            # Get video duration for cost tracking
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
            try:
                # Extract file path from video URL
                video_url = video["video_url"]
                # Get everything after /video-analyzer/ in the URL
                file_path = video_url.split(f"{settings.STORAGE_BUCKET}/")[-1]
                
                logger.info(f"Downloading video from path: {file_path}")
                
                # Download video to get duration
                if not download_file(file_path, temp_file.name):
                    raise Exception("Failed to download video for duration check")
                
                _, duration, processing_cost = validate_video_duration(temp_file.name)
                logger.info(f"Processing video duration: {duration:.2f} minutes, cost: ${processing_cost:.2f}")
                
                # Check user's remaining free minutes
                user_details = await get_user_details(current_user["id"])
                if not user_details:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="User details not found"
                    )
                
                minutes_remaining = user_details["minutes_remaining"]
                if minutes_remaining < duration and processing_cost > 0:
                    raise HTTPException(
                        status_code=status.HTTP_402_PAYMENT_REQUIRED,
                        detail=f"Insufficient free minutes. You have {minutes_remaining:.2f} minutes remaining, but the video is {duration:.2f} minutes long. Please upgrade your account or use a shorter video."
                    )
                
            finally:
                if temp_file and os.path.exists(temp_file.name):
                    os.unlink(temp_file.name)
            
            # Generate subtitles
            subtitle_result = await subtitle_service.generate_subtitles(
                video_url=video["video_url"],
                video_uuid=video_uuid,
                language=request.language
            )
            
            if not subtitle_result or "subtitle_url" not in subtitle_result:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to generate subtitles"
                )
            
            # Save subtitle metadata
            subtitle_data = {
                "uuid": str(uuid.uuid4()),
                "video_id": video["id"],
                "subtitle_url": subtitle_result["subtitle_url"],
                "format": "srt",
                "language": request.language.value
            }
            
            saved_subtitle = await save_subtitle(subtitle_data)
            if not saved_subtitle:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to save subtitle metadata"
                )
            
            # Update user's usage statistics
            if not await update_user_usage(current_user["id"], duration, processing_cost):
                logger.error(f"Failed to update usage statistics for user {current_user['id']}")
            
            # Update video status to completed
            if not await update_video_status(video_uuid, "completed"):
                logger.warning(f"Failed to update video status to completed for video {video_uuid}")
            
            return SubtitleGenerationResponse(
                message="Subtitles generated successfully",
                video_uuid=video_uuid,
                subtitle_uuid=subtitle_data["uuid"],
                subtitle_url=subtitle_result["subtitle_url"],
                language=request.language,
                status="completed",
                duration_minutes=round(duration, 2),
                processing_cost=round(processing_cost, 2),
                detail=f"Successfully generated {request.language} subtitles. Cost: ${processing_cost:.2f} for {duration:.2f} minutes"
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error generating subtitles: {str(e)}")
            # Update video status to failed
            await update_video_status(video_uuid, "failed")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate subtitles: {str(e)}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in generate_subtitles: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@router.delete("/{video_uuid}", response_model=VideoDeleteResponse, status_code=status.HTTP_200_OK)
async def delete_video(
    video_uuid: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a video and its associated data."""
    try:
        # Validate UUID format
        try:
            uuid.UUID(video_uuid)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid video UUID format"
            )
        
        # Get video details from database
        video = await get_video_by_uuid(video_uuid)
        if not video:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video not found"
            )
        
        # Check if user owns the video
        if video["user_id"] != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this video"
            )
        
        # Delete from storage
        try:
            # Extract file path from video URL
            video_path = video["video_url"].split(f"{settings.STORAGE_BUCKET}/")[-1]
            logger.info(f"Attempting to delete video file: {video_path}")
            
            # Delete video file
            if not delete_file(video_path):
                logger.error(f"Failed to delete video file from storage: {video_path}")
            
            # Get all subtitles for this video from database
            subtitles = await get_user_subtitles(current_user["id"])
            if subtitles:
                for subtitle in subtitles:
                    if subtitle["video_uuid"] == video_uuid:
                        subtitle_path = subtitle["subtitle_url"].split(f"{settings.STORAGE_BUCKET}/")[-1]
                        logger.info(f"Attempting to delete subtitle file: {subtitle_path}")
                        if not delete_file(subtitle_path):
                            logger.warning(f"Failed to delete subtitle file from storage: {subtitle_path}")
            
        except Exception as e:
            logger.error(f"Error deleting files from storage: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error deleting files from storage: {str(e)}"
            )
        
        # Delete video metadata from database
        if not await delete_video_metadata(video_uuid):
            logger.error("Failed to delete video metadata")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete video metadata"
            )
        
        return VideoDeleteResponse(
            message="Video and associated data deleted successfully",
            video_uuid=video_uuid
        )
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Unexpected error in delete_video: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@router.get("/", response_model=VideoListResponse, status_code=status.HTTP_200_OK)
async def list_videos(
    include_subtitles: bool = False,
    current_user: dict = Depends(get_current_user)
):
    """
    Get all videos for the current user.
    
    Parameters:
        - include_subtitles: If True, includes detailed subtitle information for each video
    """
    try:
        # Validate user ID
        user_id = current_user.get("id")
        if not user_id:
            logger.error("User ID not found in current_user")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user authentication"
            )
        
        # Get all videos for the user
        videos = await get_user_videos(user_id, include_subtitles)
        
        # Log the number of videos found
        logger.info(f"Found {len(videos)} videos for user {user_id}")
        
        return VideoListResponse(
            message="Videos retrieved successfully",
            count=len(videos),
            videos=[VideoResponse(**video) for video in videos]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving videos: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve videos: {str(e)}"
        ) 