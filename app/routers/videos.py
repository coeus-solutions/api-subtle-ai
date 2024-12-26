from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import JSONResponse
from typing import List
import os
import uuid
from datetime import datetime
import logging
from app.core.config import settings
from app.services.subtitle_service import subtitle_service
from app.utils.s3 import get_s3_client
from app.utils.database import (
    save_video_metadata,
    get_video_by_uuid,
    update_video_status,
    delete_video_metadata,
    save_subtitle,
    get_user_videos
)
from app.routers.auth import get_current_user
from app.models.models import (
    VideoUploadResponse, 
    SubtitleGenerationResponse, 
    VideoDeleteResponse,
    VideoListResponse,
    VideoResponse
)

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/upload", response_model=VideoUploadResponse, status_code=status.HTTP_200_OK)
async def upload_video(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload a video file to Supabase storage."""
    s3_client = None
    content = None
    file_path = None    

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
                detail=f"File size exceeds maximum allowed size of {settings.MAX_VIDEO_SIZE} bytes"
            )
        
        # Validate file type
        if file.content_type not in settings.ALLOWED_VIDEO_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type {file.content_type} not allowed. Allowed types: {settings.ALLOWED_VIDEO_TYPES}"
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
        try:
            s3_client = get_s3_client()
            s3_client.put_object(
                Bucket=settings.STORAGE_BUCKET,
                Key=file_path,
                Body=content,
                ContentType=file.content_type
            )
        except Exception as e:
            logger.error(f"Error uploading to storage: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error uploading to storage: {str(e)}"
            )
        
        # Generate public URL
        file_url = f"{settings.SUPABASE_STORAGE_URL}/object/public/{settings.STORAGE_BUCKET}/{file_path}"
        
        # Save video metadata to database
        try:
            video_data = {
                "uuid": video_uuid,
                "user_id": current_user["id"],
                "video_url": file_url,
            }            

            saved_video = await save_video_metadata(video_data)
            if not saved_video:
                # Clean up uploaded file if database save fails
                if s3_client and file_path:
                    try:
                        s3_client.delete_object(
                            Bucket=settings.STORAGE_BUCKET,
                            Key=file_path
                        )
                    except Exception as e:
                        logger.error(f"Error cleaning up file after failed metadata save: {str(e)}")
                
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to save video metadata"
                )
        except Exception as e:
            # Clean up uploaded file if database save fails
            if s3_client and file_path:
                try:
                    s3_client.delete_object(
                        Bucket=settings.STORAGE_BUCKET,
                        Key=file_path
                    )
                except Exception as cleanup_error:
                    logger.error(f"Error cleaning up file after failed metadata save: {str(cleanup_error)}")
            
            logger.error(f"Error saving video metadata: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error saving video metadata: {str(e)}"
            )
        
        return VideoUploadResponse(
            message="Video uploaded successfully",
            video_uuid=video_uuid,
            file_url=file_url,
            status="queued"
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
        # Clean up the file content from memory
        if content:
            del content

@router.post("/{video_uuid}/generate_subtitles", response_model=SubtitleGenerationResponse, status_code=status.HTTP_200_OK)
async def generate_subtitles(
    video_uuid: str,
    current_user: dict = Depends(get_current_user)
):
    """Generate subtitles for a specific video."""
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
            # Generate subtitles
            subtitle_result = await subtitle_service.generate_subtitles(
                video_url=video["video_url"],
                video_uuid=video_uuid
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
                "format": "srt"
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
            
            return SubtitleGenerationResponse(
                message="Subtitles generated successfully",
                video_uuid=video_uuid,
                subtitle_uuid=subtitle_data["uuid"],
                subtitle_url=subtitle_result["subtitle_url"],
                status="completed"
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
            s3_client = get_s3_client()
            
            # Extract file path from video URL
            file_path = video["video_url"].split("/")[-1]
            
            # Delete video file
            s3_client.delete_object(
                Bucket=settings.STORAGE_BUCKET,
                Key=file_path
            )
            
            # Try to delete subtitle file if it exists
            subtitle_path = f"subtitles/{os.path.splitext(os.path.basename(file_path))[0]}.srt"
            try:
                s3_client.delete_object(
                    Bucket=settings.STORAGE_BUCKET,
                    Key=subtitle_path
                )
            except Exception as e:
                logger.warning(f"Error deleting subtitle file: {str(e)}")
            
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
async def list_videos(current_user: dict = Depends(get_current_user)):
    """Get all videos for the current user."""
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
        videos = await get_user_videos(user_id)
        
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