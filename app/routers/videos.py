from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, Form
from fastapi.responses import JSONResponse
from typing import List
import os
import uuid
from datetime import datetime
import logging
import tempfile
from app.core.config import settings
from app.services.subtitle_service import subtitle_service
from app.services.dubbing_service import dubbing_service
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
    get_user_subtitles,
    update_video_dubbing
)
from app.routers.auth import get_current_user
from app.models.models import (
    VideoUploadResponse, 
    SubtitleGenerationResponse, 
    VideoDeleteResponse,
    VideoListResponse,
    VideoResponse,
    SubtitleGenerationRequest,
    DubbingResponse,
    DubbingStatusResponse,
    SupportedLanguage,
    VideoUploadRequest
)
import json

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/upload", response_model=VideoUploadResponse, status_code=status.HTTP_200_OK)
async def upload_video(
    file: UploadFile = File(...),
    language: SupportedLanguage = Form(default=SupportedLanguage.ENGLISH),
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
    - Accepts target language for future subtitle generation
    
    Returns:
        - Video UUID and URL
        - Video duration in minutes
        - Estimated processing cost
        - Target language for subtitles
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
                "duration_minutes": duration,
                "language": language.value
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
            language=language,
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

@router.post("/{video_uuid}/generate_subtitles", status_code=status.HTTP_200_OK)
async def generate_subtitles(
    video_uuid: str,
    request: SubtitleGenerationRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Generate subtitles for a specific video.
    
    - Uses the video's saved target language for subtitle generation
    - Optional video dubbing through ElevenLabs API
    - Cost: $0.10 per minute of video
    - First 50 minutes (worth $5.00) are free
    - Returns subtitle file in SRT format
    
    Parameters:
        - video_uuid: UUID of the uploaded video
        - enable_dubbing: Whether to enable video dubbing (optional)
    
    Returns:
        - Subtitle UUID and URL
        - Processing status
        - Video duration and actual cost
        - Dubbing information (if enabled)
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
        
        # Check if video is in a valid state for processing
        if video["status"] not in ["queued", "uploaded", "failed"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot process video in '{video['status']}' status"
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
            
            # Choose processing flow based on dubbing flag
            if request.enable_dubbing:
                # Dubbing Flow
                logger.info(f"Starting dubbing flow for video {video_uuid} in language {video['language']}")

                # Create dubbing job using video's saved language
                dubbing_result = await dubbing_service.create_dubbing(
                    video_url=video["video_url"],
                    source_lang="auto",  # Auto-detect source language
                    target_lang=video["language"]  # Use language from video record
                )
                
                if not dubbing_result or "dubbing_id" not in dubbing_result:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to create dubbing job"
                    )
                
                # Update video with dubbing information
                dubbing_info = {
                    "dubbing_id": dubbing_result["dubbing_id"],
                    "is_dubbed_audio": False  # Will be set to True when polling completes
                }
                
                if not await update_video_dubbing(video_uuid, dubbing_info):
                    logger.error(f"Failed to update video dubbing info for {video_uuid}")
                
                # Update video status to processing
                if not await update_video_status(video_uuid, "processing"):
                    logger.warning(f"Failed to update video status for video {video_uuid}")
                
                # Update user's usage statistics
                if not await update_user_usage(current_user["id"], duration, processing_cost):
                    logger.error(f"Failed to update usage statistics for user {current_user['id']}")
                
                return SubtitleGenerationResponse(
                    message="Video dubbing initiated successfully",
                    video_uuid=video_uuid,
                    dubbing_id=dubbing_result["dubbing_id"],
                    language=video.get("language", "en"),
                    status="processing",
                    duration_minutes=round(duration, 2),
                    processing_cost=round(processing_cost, 2),
                    expected_duration_sec=dubbing_result.get("expected_duration_sec"),
                    detail=f"Dubbing job created successfully. Use the polling endpoint to check status."
                )
                
            else:
                # Subtitle Generation Flow
                logger.info(f"Starting subtitle generation flow for video {video_uuid} in language {video['language']}")
                
                # Generate subtitles
                subtitle_result = await subtitle_service.generate_subtitles(
                    video_url=video["video_url"],
                    video_uuid=video_uuid,
                    language=video["language"]
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
                    "language": video["language"]
                }
                
                saved_subtitle = await save_subtitle(subtitle_data)
                if not saved_subtitle:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to save subtitle metadata"
                    )
                
                # Update video status to completed
                if not await update_video_status(video_uuid, "completed"):
                    logger.warning(f"Failed to update video status to completed for video {video_uuid}")
                
                # Update user's usage statistics
                if not await update_user_usage(current_user["id"], duration, processing_cost):
                    logger.error(f"Failed to update usage statistics for user {current_user['id']}")
                
                return SubtitleGenerationResponse(
                    message="Subtitles generated successfully",
                    video_uuid=video_uuid,
                    subtitle_uuid=subtitle_data["uuid"],
                    subtitle_url=subtitle_result["subtitle_url"],
                    language=video.get("language", "en"),
                    status="completed",
                    duration_minutes=round(duration, 2),
                    processing_cost=round(processing_cost, 2),
                    detail=f"Successfully generated {video['language']} subtitles. Cost: ${processing_cost:.2f} for {duration:.2f} minutes"
                )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error processing video: {str(e)}")
            # Update video status to failed
            await update_video_status(video_uuid, "failed")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to process video: {str(e)}"
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
    """Delete a video and all its associated data (subtitles and dubbed video)."""
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
        
        # Delete all associated files from storage
        try:
            deleted_files = []
            failed_files = []
            
            # 1. Delete original video file
            if video["video_url"]:
                video_path = video["video_url"].split(f"{settings.STORAGE_BUCKET}/")[-1]
                logger.info(f"Attempting to delete original video file: {video_path}")
                if delete_file(video_path):
                    deleted_files.append("original video")
                else:
                    failed_files.append("original video")
            
            # 2. Delete dubbed video if exists
            if video.get("dubbed_video_url"):
                dubbed_path = video["dubbed_video_url"].split(f"{settings.STORAGE_BUCKET}/")[-1]
                logger.info(f"Attempting to delete dubbed video file: {dubbed_path}")
                if delete_file(dubbed_path):
                    deleted_files.append("dubbed video")
                else:
                    failed_files.append("dubbed video")
            
            # 3. Get and delete all subtitles for this video
            subtitles = await get_user_subtitles(current_user["id"])
            if subtitles:
                for subtitle in subtitles:
                    if subtitle["video_uuid"] == video_uuid:
                        subtitle_path = subtitle["subtitle_url"].split(f"{settings.STORAGE_BUCKET}/")[-1]
                        logger.info(f"Attempting to delete subtitle file: {subtitle_path}")
                        if delete_file(subtitle_path):
                            deleted_files.append(f"subtitle ({subtitle.get('language', 'unknown')})")
                        else:
                            failed_files.append(f"subtitle ({subtitle.get('language', 'unknown')})")
            
            if failed_files:
                logger.warning(f"Failed to delete some files: {', '.join(failed_files)}")
            
        except Exception as e:
            logger.error(f"Error deleting files from storage: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error deleting files from storage: {str(e)}"
            )
        
        # Delete video metadata from database (this will cascade delete subtitles)
        if not await delete_video_metadata(video_uuid):
            logger.error("Failed to delete video metadata")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete video metadata"
            )
        
        # Prepare success message
        detail = f"Successfully deleted: {', '.join(deleted_files)}"
        if failed_files:
            detail += f". Failed to delete: {', '.join(failed_files)}"
        
        return VideoDeleteResponse(
            message="Video and associated data deleted successfully",
            video_uuid=video_uuid,
            detail=detail
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
        
        # Format the response to include dubbing information
        formatted_videos = []
        for video in videos:
            video_data = {
                **video,  # Include all existing video data
                "dubbed_video_url": video.get("dubbed_video_url"),  # Include dubbed video URL
                "dubbing_id": video.get("dubbing_id"),  # Include dubbing ID
                "is_dubbed_audio": video.get("is_dubbed_audio", False)  # Include dubbing status
            }
            formatted_videos.append(VideoResponse(**video_data))
        
        return VideoListResponse(
            message="Videos retrieved successfully",
            count=len(formatted_videos),
            videos=formatted_videos
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving videos: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve videos: {str(e)}"
        )

@router.get("/{video_uuid}/dubbing/{dubbing_id}/status", response_model=DubbingStatusResponse, status_code=status.HTTP_200_OK)
async def check_dubbing_status(
    video_uuid: str,
    dubbing_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Check the status of a dubbing job.
    
    - Polls ElevenLabs API for dubbing status
    - Returns current status and progress information
    - Status values from ElevenLabs: "dubbing" (in progress), "dubbed" (completed), "failed"
    
    Parameters:
        - video_uuid: UUID of the video
        - dubbing_id: ID of the dubbing job from ElevenLabs
    
    Returns:
        - Status of the dubbing job
        - Expected duration in seconds
        - Progress information
    """
    try:
        # Validate and get video (reuse existing validation code)
        video = await validate_video_access(video_uuid, dubbing_id, current_user["id"])
        
        # Check dubbing status from ElevenLabs
        dubbing_status = await dubbing_service.get_dubbing_status(dubbing_id)
        if not dubbing_status:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get dubbing status from ElevenLabs"
            )
        
        logger.info(f"Dubbing status response: {json.dumps(dubbing_status, indent=2)}")
        status_value = dubbing_status.get("status", "dubbing")  # Default to "dubbing" if not provided
        
        # If failed, update video status
        if status_value == "failed":
            await update_video_status(video_uuid, "failed")
            error_detail = dubbing_status.get("error", "Unknown error")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Dubbing process failed at ElevenLabs: {error_detail}"
            )
        
        return DubbingStatusResponse(
            message=f"Dubbing status: {status_value}",
            video_uuid=video_uuid,
            dubbing_id=dubbing_id,
            language=video.get("language", "en"),
            status=status_value,  # Use original ElevenLabs status
            duration_minutes=video.get("duration_minutes", 0),
            detail=f"Current status from ElevenLabs: {status_value}",
            expected_duration_sec=dubbing_status.get("duration", 0)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in check_dubbing_status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@router.get("/{video_uuid}/dubbing/{dubbing_id}/video", response_model=DubbingResponse, status_code=status.HTTP_200_OK)
async def get_dubbed_video(
    video_uuid: str,
    dubbing_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get the dubbed video once dubbing is completed.
    
    - Verifies dubbing is completed (status must be "dubbed")
    - Downloads dubbed video from ElevenLabs
    - Uploads to storage and updates video record
    
    Parameters:
        - video_uuid: UUID of the video
        - dubbing_id: ID of the dubbing job from ElevenLabs
    
    Returns:
        - Dubbed video URL
        - Processing information
    """
    try:
        # Validate and get video (reuse existing validation code)
        video = await validate_video_access(video_uuid, dubbing_id, current_user["id"])
        
        # Check if we already have the dubbed video
        if video.get("dubbed_video_url"):
            return DubbingResponse(
                message="Dubbed video already available",
                video_uuid=video_uuid,
                dubbing_id=dubbing_id,
                dubbed_video_url=video["dubbed_video_url"],
                language=video.get("language", "en"),
                status="dubbed",  # Use ElevenLabs status
                duration_minutes=video.get("duration_minutes", 0),
                detail="Dubbed video already processed and stored"
            )
        
        # Check current dubbing status
        dubbing_status = await dubbing_service.get_dubbing_status(dubbing_id)
        if not dubbing_status:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get dubbing status"
            )
        
        status_value = dubbing_status.get("status", "dubbing")  # Default to "dubbing" if not provided
        if status_value != "dubbed":  # ElevenLabs uses "dubbed" for completed status
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Dubbing is not completed yet. Current status: {status_value}"
            )
        
        # Get the dubbed video
        dubbed_url = await dubbing_service.get_dubbed_audio(
            dubbing_id=dubbing_id,
            target_lang=video.get("language", "en"),
            video_uuid=video_uuid
        )
        
        if not dubbed_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get dubbed video"
            )
        
        # Update video record with dubbed file URL
        dubbing_info = {
            "dubbing_id": dubbing_id,
            "dubbed_video_url": dubbed_url,
            "is_dubbed_audio": True
        }
        
        if not await update_video_dubbing(video_uuid, dubbing_info):
            logger.error(f"Failed to update video dubbing info for {video_uuid}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update video with dubbed file information"
            )
        
        # Update video status to completed
        if not await update_video_status(video_uuid, "completed"):
            logger.warning(f"Failed to update video status to completed for video {video_uuid}")
        
        return DubbingResponse(
            message="Dubbed video retrieved successfully",
            video_uuid=video_uuid,
            dubbing_id=dubbing_id,
            dubbed_video_url=dubbed_url,
            language=video.get("language", "en"),
            status="dubbed",  # Use ElevenLabs status
            duration_minutes=video.get("duration_minutes", 0),
            detail="Successfully downloaded and stored dubbed video"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_dubbed_video: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@router.get("/{video_uuid}/get-transcript-for-dub/{dubbing_id}", response_model=SubtitleGenerationResponse, status_code=status.HTTP_200_OK)
async def get_transcript_for_dub(
    video_uuid: str,
    dubbing_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get the transcript for a dubbed video.
    
    - Retrieves transcript from ElevenLabs API
    - Saves transcript as SRT file in storage
    - Creates subtitle record in database
    
    Parameters:
        - video_uuid: UUID of the video
        - dubbing_id: ID of the dubbing job from ElevenLabs
    
    Returns:
        - Subtitle UUID and URL
        - Processing status
        - Video duration and language
    """
    try:
        # Validate and get video (reuse existing validation code)
        video = await validate_video_access(video_uuid, dubbing_id, current_user["id"])
        
        # Get transcript from ElevenLabs
        transcript_content = await dubbing_service.get_transcript(
            dubbing_id=dubbing_id,
            language_code=video.get("language", "en"),
            format_type="srt"
        )
        
        if not transcript_content:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get transcript from ElevenLabs"
            )
        
        # Generate subtitle file path
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        subtitle_filename = f"{timestamp}_{video_uuid[:8]}_transcript_{video.get('language', 'en')}.srt"
        subtitle_path = f"subtitles/{subtitle_filename}"
        
        # Upload transcript to storage
        if not upload_file(subtitle_path, transcript_content.encode('utf-8'), 'text/plain'):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload transcript file"
            )
        
        # Generate subtitle URL
        subtitle_url = get_file_url(subtitle_path)
        
        # Save subtitle metadata
        subtitle_data = {
            "uuid": str(uuid.uuid4()),
            "video_id": video["id"],
            "subtitle_url": subtitle_url,
            "format": "srt",
            "language": video.get("language", "en")
        }
        
        saved_subtitle = await save_subtitle(subtitle_data)
        if not saved_subtitle:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save subtitle metadata"
            )
        
        return SubtitleGenerationResponse(
            message="Transcript retrieved successfully",
            video_uuid=video_uuid,
            subtitle_uuid=subtitle_data["uuid"],
            subtitle_url=subtitle_url,
            language=video.get("language", "en"),
            status="completed",
            duration_minutes=video.get("duration_minutes", 0),
            detail=f"Successfully retrieved transcript in {video.get('language', 'en')}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_transcript_for_dub: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

async def validate_video_access(video_uuid: str, dubbing_id: str, user_id: int):
    """Helper function to validate video access and dubbing ID."""
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
    if video["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this video"
        )
    
    # Check if this dubbing_id matches the one stored for the video
    if not video.get("dubbing_id") or video["dubbing_id"] != dubbing_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid dubbing ID for this video"
        )
    
    return video 