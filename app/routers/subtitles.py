from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, JSONResponse
from typing import List
import logging
import uuid
import tempfile
from app.routers.auth import get_current_user
from app.utils.database import get_user_subtitles, get_subtitle_by_uuid
from app.utils.s3 import get_s3_client
from app.core.config import settings
from datetime import datetime
from app.models.models import ListSubtitlesResponse, SubtitleResponse

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/", response_model=ListSubtitlesResponse, status_code=status.HTTP_200_OK)
async def list_subtitles(current_user: dict = Depends(get_current_user)):
    """Get all subtitles for the current user."""
    try:
        # Validate user ID
        user_id = current_user.get("id")
        if not user_id:
            logger.error("User ID not found in current_user")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user authentication"
            )
        
        # Get all subtitles for the user
        subtitles = await get_user_subtitles(user_id)
        
        # Log the number of subtitles found
        logger.info(f"Found {len(subtitles)} subtitles for user {user_id}")
        
        return ListSubtitlesResponse(
            message="Subtitles retrieved successfully",
            count=len(subtitles),
            subtitles=[SubtitleResponse(**subtitle) for subtitle in subtitles]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving subtitles: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve subtitles: {str(e)}"
        )

@router.get("/{subtitle_uuid}")
async def download_subtitle(
    subtitle_uuid: str,
    current_user: dict = Depends(get_current_user)
):
    """Download a subtitle file."""
    try:
        # Validate UUID format
        try:
            uuid.UUID(subtitle_uuid)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid subtitle UUID format"
            )
        
        # Get subtitle details from database
        subtitle = await get_subtitle_by_uuid(subtitle_uuid)
        if not subtitle:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subtitle not found"
            )
        
        # Check if user owns the subtitle
        if subtitle["user_id"] != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to download this subtitle"
            )
        
        try:
            # Extract file path from subtitle URL
            file_path = subtitle["subtitle_url"].split("/")[-1]
            
            # Create a temporary file to store the subtitle
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f'.{subtitle["format"]}')
            
            # Download subtitle file from storage
            s3_client = get_s3_client()
            s3_client.download_file(
                Bucket=settings.STORAGE_BUCKET,
                Key=f"subtitles/{file_path}",
                Filename=temp_file.name
            )
            
            return FileResponse(
                path=temp_file.name,
                filename=file_path,
                media_type="application/x-subrip",
                background=None  # This ensures the file is deleted after sending
            )
            
        except Exception as e:
            logger.error(f"Error downloading subtitle file: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error downloading subtitle file: {str(e)}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in download_subtitle: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        ) 