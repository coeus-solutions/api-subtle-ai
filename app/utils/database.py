from supabase import create_client
from app.core.config import settings
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Initialize Supabase client
supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

def serialize_datetime(dt):
    """Serialize datetime objects to ISO format strings."""
    if isinstance(dt, datetime):
        return dt.isoformat()
    return dt

def serialize_dict(d):
    """Serialize dictionary values that are datetime objects."""
    return {k: serialize_datetime(v) for k, v in d.items()}

async def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Get user by email."""
    try:
        result = supabase.table('users').select('*').eq('email', email).execute()
        return serialize_dict(result.data[0]) if result.data else None
    except Exception as e:
        print(f"Error getting user by email: {str(e)}")
        return None

async def create_user(user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Create a new user."""
    try:
        serialized_data = serialize_dict(user_data)
        result = supabase.table('users').insert(serialized_data).execute()
        return serialize_dict(result.data[0]) if result.data else None
    except Exception as e:
        print(f"Error creating user: {str(e)}")
        return None

async def save_video_metadata(video_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Save video metadata to the database."""
    try:
        # Prepare video data according to schema
        db_video_data = {
            "uuid": video_data["uuid"],
            "user_id": video_data.get("user_id", None),  # This should be set based on authenticated user
            "video_url": video_data["video_url"],
        }
        
        # Insert data
        result = supabase.table('videos').insert(db_video_data).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"Error saving video metadata: {str(e)}")
        return None

async def get_video_by_uuid(video_uuid: str) -> Optional[Dict[str, Any]]:
    """Get video details by UUID."""
    try:
        result = supabase.table('videos').select('*').eq('uuid', video_uuid).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"Error getting video by UUID: {str(e)}")
        return None

async def update_video_status(video_uuid: str, status: str) -> bool:
    """Update video status."""
    try:
        result = supabase.table('videos').update({
            'status': status,
            'updated_at': datetime.utcnow().isoformat()
        }).eq('uuid', video_uuid).execute()
        return bool(result.data)
    except Exception as e:
        print(f"Error updating video status: {str(e)}")
        return False

async def delete_video_metadata(video_uuid: str) -> bool:
    """Delete video metadata from database."""
    try:
        result = supabase.table('videos').delete().eq('uuid', video_uuid).execute()
        return bool(result.data)
    except Exception as e:
        print(f"Error deleting video metadata: {str(e)}")
        return False

async def save_subtitle(subtitle_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Save subtitle metadata to the database."""
    try:
        # Prepare subtitle data according to schema
        db_subtitle_data = {
            "uuid": subtitle_data["uuid"],
            "video_id": subtitle_data["video_id"],
            "subtitle_url": subtitle_data["subtitle_url"],
            "format": subtitle_data.get("format", "srt"),
        }
        
        # Insert data
        result = supabase.table('subtitles').insert(db_subtitle_data).execute()
        if not result.data:
            logger.error("No data returned after subtitle insertion")
            return None
            
        return result.data[0]
    except Exception as e:
        logger.error(f"Error saving subtitle metadata: {str(e)}")
        return None

async def get_user_subtitles(user_id: int) -> List[Dict[str, Any]]:
    """Get all subtitles for a user."""
    try:
        # First get the videos for the user
        videos_result = supabase.table('videos')\
            .select('id, uuid')\
            .eq('user_id', user_id)\
            .execute()
        
        if not videos_result.data:
            logger.info(f"No videos found for user {user_id}")
            return []
        
        # Get video IDs
        video_ids = [video['id'] for video in videos_result.data]
        
        # Get subtitles for these videos
        subtitles_result = supabase.table('subtitles')\
            .select('*')\
            .in_('video_id', video_ids)\
            .execute()
        
        if not subtitles_result.data:
            logger.info(f"No subtitles found for user's videos")
            return []
        
        # Create a map of video_id to video_uuid for easy lookup
        video_uuid_map = {video['id']: video['uuid'] for video in videos_result.data}
        
        # Format the response
        formatted_data = []
        for subtitle in subtitles_result.data:
            try:
                video_uuid = video_uuid_map.get(subtitle['video_id'])
                if video_uuid:
                    formatted_item = {
                        "uuid": subtitle["uuid"],
                        "video_uuid": video_uuid,
                        "subtitle_url": subtitle["subtitle_url"],
                        "format": subtitle.get("format", "srt"),
                        "created_at": subtitle.get("created_at"),
                        "updated_at": subtitle.get("updated_at")
                    }
                    formatted_data.append(formatted_item)
            except KeyError as ke:
                logger.error(f"Missing key in subtitle data: {str(ke)}")
                continue
            except Exception as e:
                logger.error(f"Error formatting subtitle item: {str(e)}")
                continue
        
        return formatted_data
    except Exception as e:
        logger.error(f"Error getting user subtitles: {str(e)}")
        return []

async def get_subtitle_by_uuid(subtitle_uuid: str) -> Optional[Dict[str, Any]]:
    """Get subtitle details by UUID."""
    try:
        # Get subtitle details
        subtitle_result = supabase.table('subtitles').select('*').eq('uuid', subtitle_uuid).execute()
        
        if not subtitle_result.data:
            logger.info(f"No subtitle found with UUID: {subtitle_uuid}")
            return None
            
        subtitle = subtitle_result.data[0]
        
        # Get associated video to check ownership
        video_result = supabase.table('videos').select('uuid, user_id').eq('id', subtitle['video_id']).execute()
        
        if not video_result.data:
            logger.error(f"No video found for subtitle {subtitle_uuid}")
            return None
            
        video = video_result.data[0]
        
        # Return combined data
        return {
            **subtitle,
            "video_uuid": video["uuid"],
            "user_id": video["user_id"]
        }
    except Exception as e:
        logger.error(f"Error getting subtitle by UUID: {str(e)}")
        return None

async def get_user_videos(user_id: int) -> List[Dict[str, Any]]:
    """Get all videos for a user."""
    try:
        # Get videos for the user
        result = supabase.table('videos')\
            .select('*')\
            .eq('user_id', user_id)\
            .order('created_at', desc=True)\
            .execute()
        
        if not result.data:
            logger.info(f"No videos found for user {user_id}")
            return []
        
        # Format the response
        formatted_data = []
        for video in result.data:
            try:
                formatted_item = {
                    "uuid": str(video["uuid"]),
                    "video_url": video["video_url"],
                    "status": video.get("status", "queued"),
                    "created_at": video.get("created_at"),
                    "updated_at": video.get("updated_at")
                }
                formatted_data.append(formatted_item)
            except KeyError as ke:
                logger.error(f"Missing key in video data: {str(ke)}")
                continue
            except Exception as e:
                logger.error(f"Error formatting video item: {str(e)}")
                continue
        
        return formatted_data
    except Exception as e:
        logger.error(f"Error getting user videos: {str(e)}")
        return [] 