import aiohttp
import os
import tempfile
from datetime import datetime
import uuid
from urllib.parse import urlparse
from app.core.config import settings
from app.utils.s3 import upload_file, download_file, get_file_url
import logging

# Set up logging
logger = logging.getLogger(__name__)

class SubtitleService:
    def __init__(self):
        self.openai_api_key = settings.OPENAI_API_KEY
        self.language_names = {
            "en": "English",
            "de": "German",
            "es": "Spanish",
            "fr": "French",
            "ja": "Japanese",
            "ru": "Russian"
        }
    
    def _extract_file_path_from_url(self, url: str) -> str:
        """Extract the file path from the Supabase storage URL."""
        try:
            # Get everything after /video-analyzer/ in the URL
            file_path = url.split(f"{settings.STORAGE_BUCKET}/")[-1]
            logger.info(f"Extracted file path: {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Error extracting file path from URL: {url}, Error: {str(e)}")
            raise Exception(f"Invalid storage URL format: {str(e)}")
    
    async def _translate_with_gpt(self, srt_content: str, target_language: str) -> str:
        """Translate SRT content using GPT-3.5 while preserving format."""
        try:
            # Get full language name
            language_name = self.language_names.get(target_language, "English")
            
            # Prepare the prompt for GPT
            system_prompt = f"""You are a professional subtitle translator. 
            Translate the following SRT format subtitles to {language_name}.
            Maintain the exact SRT format including timecodes and numbers.
            Only translate the text content, keep timecodes and numbers unchanged."""

            user_prompt = f"Here's the SRT content to translate:\n\n{srt_content}"

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.openai_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-3.5-turbo",
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        "temperature": 0.3  # Lower temperature for more consistent translations
                    }
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"GPT API error during translation: {error_text}")
                    
                    response_data = await response.json()
                    translated_text = response_data['choices'][0]['message']['content']
                    return translated_text.strip()

        except Exception as e:
            logger.error(f"Error translating with GPT: {str(e)}")
            raise Exception(f"Failed to translate subtitles: {str(e)}")
    
    async def generate_subtitles(self, video_url: str, video_uuid: str, language: str = "en") -> dict:
        """Generate subtitles for a video using OpenAI's Whisper API and GPT for translation."""
        temp_file = None
        try:
            # Extract file path from video URL
            try:
                file_path = self._extract_file_path_from_url(video_url)
                logger.info(f"Extracted file path: {file_path}")
            except Exception as e:
                raise Exception(f"Failed to extract file path from URL: {str(e)}")
            
            # Download video file to temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
            if not download_file(file_path, temp_file.name):
                raise Exception("Failed to download video from storage")
            
            try:
                # First, transcribe the audio to English using Whisper
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
                                raise Exception(f"OpenAI API error during transcription: {error_text}")
                            
                            transcribed_text = await response.text()
                
                # Always translate to target language using GPT
                logger.info(f"Translating subtitles to {language} using GPT")
                subtitles = await self._translate_with_gpt(transcribed_text, language)
                
                # Generate subtitle file path with language code
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                subtitle_filename = f"{timestamp}_{video_uuid[:8]}_{language}.srt"
                subtitle_path = f"subtitles/{subtitle_filename}"
                
                # Upload subtitles to Supabase storage
                if not upload_file(subtitle_path, subtitles.encode('utf-8'), 'text/plain'):
                    raise Exception("Failed to upload subtitle file")
                
                # Generate subtitle URL
                subtitle_url = get_file_url(subtitle_path)
                
                return {
                    "status": "success",
                    "subtitle_url": subtitle_url,
                    "subtitle_path": subtitle_path,
                    "language": language
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
