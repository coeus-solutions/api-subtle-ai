import logging
import tempfile
import os
from app.core.config import settings
from typing import Optional, Dict, Any
from app.utils.s3 import upload_file, get_file_url
from datetime import datetime
import aiohttp
import json

# Set up logging
logger = logging.getLogger(__name__)

class DubbingService:
    def __init__(self):
        self.api_key = settings.ELEVENLABS_API_KEY
        self.api_url = "https://api.elevenlabs.io/v1/dubbing"
    
    async def create_dubbing(self, video_url: str, source_lang: str, target_lang: str) -> Optional[Dict[str, Any]]:
        """
        Create a dubbing job using ElevenLabs API
        
        Args:
            video_url: URL of the source video
            source_lang: Source language code
            target_lang: Target language code (should be the value from SupportedLanguage enum)
            
        Returns:
            Dictionary containing dubbing_id and expected_duration_sec if successful,
            None if failed
        """
        try:
            headers = {
                "xi-api-key": self.api_key
            }
            
            logger.info(f"Creating dubbing job for video: {video_url}")
            logger.info(f"Source language: {source_lang}, Target language: {target_lang}")
            
            form_data = aiohttp.FormData()
            form_data.add_field('source_url', video_url)
            form_data.add_field('target_lang', target_lang)
            
            logger.info(f"Making request to ElevenLabs API with URL: {self.api_url}")
            logger.info(f"Headers: {headers}")
            logger.info("Form data fields: source_url, target_lang")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    headers=headers,
                    data=form_data
                ) as response:
                    response_text = await response.text()
                    logger.info(f"ElevenLabs API raw response: {response_text}")
                    
                    if response.status != 200:
                        logger.error(f"ElevenLabs API error: {response_text}")
                        raise Exception(f"ElevenLabs API error: {response_text}")
                    
                    try:
                        result = json.loads(response_text)
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse ElevenLabs API response: {response_text}")
                        raise Exception(f"Invalid JSON response from ElevenLabs API: {str(e)}")
                    
                    logger.info(f"ElevenLabs API parsed response: {json.dumps(result, indent=2)}")
                    
                    if not result.get("dubbing_id"):
                        raise Exception("No dubbing_id in ElevenLabs API response")
                    
                    return {
                        "dubbing_id": result.get("dubbing_id"),
                        "expected_duration_sec": result.get("expected_duration_sec")
                    }
                    
        except Exception as e:
            logger.error(f"Error creating dubbing: {str(e)}")
            raise Exception(f"Failed to create dubbing job: {str(e)}")
    
    async def get_dubbing_status(self, dubbing_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a dubbing job
        
        Args:
            dubbing_id: The ID of the dubbing job
            
        Returns:
            Dictionary containing status information if successful,
            None if failed
        """
        try:
            headers = {
                "xi-api-key": self.api_key
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.api_url}/{dubbing_id}",
                    headers=headers
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Error getting dubbing status: {error_text}")
                        return None
                    
                    result = await response.json()
                    logger.info(f"ElevenLabs status response: {json.dumps(result, indent=2)}")
                    
                    # Map ElevenLabs status to our status format
                    status_mapping = {
                        "dubbed": "completed",
                        "dubbing": "processing",
                        "failed": "failed"
                    }
                    
                    # Get duration from media_metadata if it exists, otherwise default to 0
                    duration = 0
                    if result.get("media_metadata"):
                        duration = result["media_metadata"].get("duration", 0)
                    
                    return {
                        "dubbing_id": result.get("dubbing_id"),
                        "status": status_mapping.get(result.get("status", ""), "processing"),
                        "target_languages": result.get("target_languages", []),
                        "duration": duration,
                        "error": result.get("error")
                    }
                    
        except Exception as e:
            logger.error(f"Error getting dubbing status: {str(e)}")
            return None
    
    async def get_dubbed_audio(self, dubbing_id: str, target_lang: str, video_uuid: str) -> Optional[str]:
        """
        Get the dubbed audio/video file, upload it to Supabase storage, and return the URL
        
        Args:
            dubbing_id: The ID of the dubbing job
            target_lang: Target language code
            video_uuid: UUID of the original video
            
        Returns:
            URL of the uploaded dubbed file in Supabase storage if successful,
            None if failed
        """
        temp_file = None
        try:
            headers = {
                "xi-api-key": self.api_key
            }
            
            # Create a temporary file to store the dubbed content
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.api_url}/{dubbing_id}/audio/{target_lang}",
                    headers=headers
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Error getting dubbed audio: {error_text}")
                        return None
                    
                    # Stream the response content to a temporary file
                    with open(temp_file.name, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            f.write(chunk)
            
            # Generate the storage path for the dubbed file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dubbed_filename = f"{timestamp}_{video_uuid[:8]}_dubbed_{target_lang}.mp4"
            dubbed_path = f"dubbed_videos/{dubbed_filename}"
            
            # Upload the dubbed file to Supabase storage
            with open(temp_file.name, 'rb') as f:
                content = f.read()
                if not upload_file(dubbed_path, content, 'video/mp4'):
                    logger.error("Failed to upload dubbed file to storage")
                    return None
            
            # Generate and return the public URL
            dubbed_url = get_file_url(dubbed_path)
            logger.info(f"Successfully uploaded dubbed video to {dubbed_url}")
            return dubbed_url
                    
        except Exception as e:
            print(e)
            logger.error(f"Error processing dubbed audio: {str(e)}")
            return None
        finally:
            # Clean up temporary file
            if temp_file and os.path.exists(temp_file.name):
                try:
                    os.unlink(temp_file.name)
                except Exception as e:
                    logger.error(f"Error cleaning up temporary file: {str(e)}")

dubbing_service = DubbingService() 