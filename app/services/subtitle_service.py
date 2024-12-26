import aiohttp
import os
import tempfile
from datetime import datetime
import uuid
from urllib.parse import urlparse
from app.core.config import settings
from app.utils.s3 import get_s3_client
import logging

# Set up logging
logger = logging.getLogger(__name__)

class SubtitleService:
    def __init__(self):
        self.openai_api_key = settings.OPENAI_API_KEY
    
    def _extract_file_path_from_url(self, url: str) -> str:
        """Extract the file path from the Supabase storage URL."""
        try:
            # Parse the URL and split the path
            parsed_url = urlparse(url)
            path_parts = parsed_url.path.split('/')
            
            # Find the index after 'public' in the path
            try:
                public_index = path_parts.index('public')
                # Join all parts after 'public' and the bucket name
                file_path = '/'.join(path_parts[public_index + 2:])
                return file_path
            except ValueError:
                # If 'public' not found, try to get everything after the bucket name
                try:
                    bucket_index = path_parts.index(settings.STORAGE_BUCKET)
                    file_path = '/'.join(path_parts[bucket_index + 1:])
                    return file_path
                except ValueError:
                    raise Exception("Could not find file path in URL")
                
        except Exception as e:
            logger.error(f"Error extracting file path from URL: {url}, Error: {str(e)}")
            raise Exception(f"Invalid storage URL format: {str(e)}")
    
    async def generate_subtitles(self, video_url: str, video_uuid: str) -> dict:
        """Generate subtitles for a video using OpenAI's Whisper API."""
        temp_file = None
        try:
            # Extract file path from video URL
            try:
                file_path = self._extract_file_path_from_url(video_url)
                logger.info(f"Extracted file path: {file_path}")
            except Exception as e:
                raise Exception(f"Failed to extract file path from URL: {str(e)}")
            
            # Download video file using S3 client
            s3_client = get_s3_client()
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
            
            try:
                logger.info(f"Downloading file from bucket: {settings.STORAGE_BUCKET}, key: {file_path}")
                s3_client.download_file(
                    Bucket=settings.STORAGE_BUCKET,
                    Key=file_path,
                    Filename=temp_file.name
                )
            except Exception as e:
                logger.error(f"Failed to download video from storage: {str(e)}")
                raise Exception(f"Failed to download video from storage: {str(e)}")
            
            try:
                # Generate subtitles using OpenAI's Whisper API
                headers = {
                    "Authorization": f"Bearer {self.openai_api_key}"
                }
                
                async with aiohttp.ClientSession() as session:
                    with open(temp_file.name, 'rb') as audio_file:
                        form_data = aiohttp.FormData()
                        form_data.add_field('file', audio_file)
                        form_data.add_field('model', 'whisper-1')
                        form_data.add_field('response_format', 'srt')
                        
                        async with session.post(
                            'https://api.openai.com/v1/audio/transcriptions',
                            headers=headers,
                            data=form_data
                        ) as response:
                            if response.status != 200:
                                error_text = await response.text()
                                raise Exception(f"OpenAI API error: {error_text}")
                            
                            subtitles = await response.text()
                
                # Generate subtitle file path
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                subtitle_filename = f"{timestamp}_{video_uuid[:8]}.srt"
                subtitle_path = f"subtitles/{subtitle_filename}"
                
                # Upload subtitles to Supabase storage
                s3_client.put_object(
                    Bucket=settings.STORAGE_BUCKET,
                    Key=subtitle_path,
                    Body=subtitles.encode('utf-8'),
                    ContentType='text/plain'
                )
                
                # Generate subtitle URL
                subtitle_url = f"{settings.SUPABASE_STORAGE_URL}/object/public/{settings.STORAGE_BUCKET}/{subtitle_path}"
                
                return {
                    "status": "success",
                    "subtitle_url": subtitle_url,
                    "subtitle_path": subtitle_path
                }
            
            finally:
                # Clean up temporary file
                if temp_file and os.path.exists(temp_file.name):
                    os.unlink(temp_file.name)
        
        except Exception as e:
            if temp_file and os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
            raise Exception(f"Failed to generate subtitles: {str(e)}")

subtitle_service = SubtitleService() 