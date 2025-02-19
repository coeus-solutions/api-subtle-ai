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
        # Add default allowed minutes
        user_data["allowed_minutes"] = settings.ALLOWED_MINUTES_DEFAULT
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
            "user_id": video_data["user_id"],
            "video_url": video_data["video_url"],
            "original_name": video_data["original_name"],
            "duration_minutes": video_data["duration_minutes"],
            "language": video_data.get("language", "en"),
            "status": "queued"
        }
        
        # Insert data
        result = supabase.table('videos').insert(db_video_data).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error(f"Error saving video metadata: {str(e)}")
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
            "language": subtitle_data["language"]
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
            .select('id, uuid, original_name')\
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
        
        # Create a map of video_id to video info for easy lookup
        video_info_map = {video['id']: {'uuid': video['uuid'], 'original_name': video['original_name']} for video in videos_result.data}
        
        # Format the response
        formatted_data = []
        for subtitle in subtitles_result.data:
            try:
                video_info = video_info_map.get(subtitle['video_id'])
                if video_info:
                    formatted_item = {
                        "uuid": subtitle["uuid"],
                        "video_uuid": video_info['uuid'],
                        "video_original_name": video_info['original_name'],
                        "subtitle_url": subtitle["subtitle_url"],
                        "format": subtitle.get("format", "srt"),
                        "language": subtitle.get("language", "en"),
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

async def get_user_videos(user_id: int, include_subtitles: bool = False) -> List[Dict[str, Any]]:
    """Get all videos for a user with optional subtitle information."""
    try:
        # Get videos for the user
        result = supabase.table('videos')\
            .select('*, dubbed_video_url, dubbing_id, is_dubbed_audio, burned_video_url')\
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
                    "original_name": video.get("original_name"),
                    "duration_minutes": video.get("duration_minutes", 0),
                    "status": video.get("status", "queued"),
                    "created_at": video.get("created_at"),
                    "updated_at": video.get("updated_at"),
                    "has_subtitles": False,
                    "subtitle_languages": [],
                    "dubbed_video_url": video.get("dubbed_video_url"),  # Include dubbed video URL
                    "burned_video_url": video.get("burned_video_url"),  # Include burned video URL
                    "dubbing_id": video.get("dubbing_id"),  # Include dubbing ID
                    "is_dubbed_audio": video.get("is_dubbed_audio", False)  # Include dubbing status
                }

                if include_subtitles:
                    # Get subtitles for this video
                    subtitles_result = supabase.table('subtitles')\
                        .select('*')\
                        .eq('video_id', video["id"])\
                        .execute()
                    
                    if subtitles_result.data:
                        formatted_item["has_subtitles"] = True
                        formatted_item["subtitle_languages"] = list(set(sub["language"] for sub in subtitles_result.data))
                        formatted_item["subtitles"] = [{
                            "uuid": str(sub["uuid"]),
                            "language": sub["language"],
                            "subtitle_url": sub["subtitle_url"],
                            "created_at": sub.get("created_at")
                        } for sub in subtitles_result.data]

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

async def update_user_usage(user_id: int, minutes: float, cost: float) -> bool:
    """Update user's usage statistics."""
    try:
        # Get current user stats
        user_result = supabase.table('users').select('minutes_consumed, free_minutes_used, total_cost').eq('id', user_id).execute()
        if not user_result.data:
            logger.error(f"No user found with ID: {user_id}")
            return False
            
        user = user_result.data[0]
        current_minutes = float(user.get('minutes_consumed', 0))
        current_free_minutes = float(user.get('free_minutes_used', 0))
        current_total_cost = float(user.get('total_cost', 0))
        
        # Calculate new values
        new_minutes = current_minutes + minutes
        new_free_minutes = min(current_free_minutes + minutes, 50.0)  # Cap at 50 free minutes
        new_total_cost = current_total_cost + (max(0, (current_free_minutes + minutes) - 50.0) * 0.10)  # Only charge after 50 minutes
        
        # Update user stats
        result = supabase.table('users').update({
            'minutes_consumed': new_minutes,
            'free_minutes_used': new_free_minutes,
            'total_cost': new_total_cost,
            'updated_at': datetime.utcnow().isoformat()
        }).eq('id', user_id).execute()
        
        return bool(result.data)
    except Exception as e:
        logger.error(f"Error updating user usage: {str(e)}")
        return False

async def get_user_details(user_id: int) -> Optional[Dict[str, Any]]:
    """Get detailed user information including usage statistics."""
    try:
        result = supabase.table('users').select('*').eq('id', user_id).execute()
        if not result.data:
            return None
            
        user = result.data[0]
        minutes_consumed = float(user.get('minutes_consumed', 0))
        free_minutes_used = float(user.get('free_minutes_used', 0))
        total_cost = float(user.get('total_cost', 0))
        allowed_minutes = float(user.get('allowed_minutes', settings.ALLOWED_MINUTES_DEFAULT))
        
        # Calculate remaining free minutes based on user's allowed minutes
        free_minutes_remaining = max(0, allowed_minutes - free_minutes_used)
        
        return {
            "email": user["email"],
            "minutes_consumed": minutes_consumed,
            "free_minutes_used": free_minutes_used,
            "total_cost": total_cost,
            "minutes_remaining": free_minutes_remaining,
            "cost_per_minute": settings.COST_PER_MINUTE,
            "free_minutes_allocation": allowed_minutes,  # Use user's allowed minutes
            "allowed_minutes": allowed_minutes,  # Add allowed minutes to response
            "created_at": user.get("created_at"),
            "updated_at": user.get("updated_at")
        }
    except Exception as e:
        logger.error(f"Error getting user details: {str(e)}")
        return None

async def update_video_dubbing(video_uuid: str, dubbing_data: Dict[str, Any]) -> bool:
    """Update video dubbing information."""
    try:
        # Prepare update data
        update_data = {
            "dubbed_video_url": dubbing_data.get("dubbed_video_url"),
            "dubbing_id": dubbing_data.get("dubbing_id"),
            "is_dubbed_audio": dubbing_data.get("is_dubbed_audio", False)
        }
        
        # Update video record
        result = supabase.table('videos').update(update_data).eq('uuid', video_uuid).execute()
        
        if not result.data:
            logger.error(f"No data returned after updating video dubbing info for UUID: {video_uuid}")
            return False
            
        return True
    except Exception as e:
        logger.error(f"Error updating video dubbing info: {str(e)}")
        return False

async def update_video_burned_url(video_uuid: str, burned_video_url: str) -> bool:
    """Update video's burned video URL."""
    try:
        result = supabase.table('videos').update({
            'burned_video_url': burned_video_url,
            'updated_at': datetime.utcnow().isoformat()
        }).eq('uuid', video_uuid).execute()
        
        if not result.data:
            logger.error(f"No data returned after updating burned video URL for UUID: {video_uuid}")
            return False
            
        return True
    except Exception as e:
        logger.error(f"Error updating burned video URL: {str(e)}")
        return False

async def update_video_urls(video_uuid: str, processed_video_url: str) -> bool:
    """Update both dubbed_video_url and burned_video_url for a video."""
    try:
        update_data = {
            "dubbed_video_url": processed_video_url,
            "burned_video_url": processed_video_url,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        result = supabase.table('videos').update(update_data).eq('uuid', video_uuid).execute()
        
        if not result.data:
            logger.error(f"No data returned after updating video URLs for UUID: {video_uuid}")
            return False
            
        return True
    except Exception as e:
        logger.error(f"Error updating video URLs: {str(e)}")
        return False 