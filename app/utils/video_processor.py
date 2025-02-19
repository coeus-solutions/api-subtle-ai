import ffmpeg
import tempfile
import os
import logging
from datetime import datetime
from typing import Optional, Tuple
from app.core.config import settings
from app.utils.s3 import upload_file, download_file, get_file_url

logger = logging.getLogger(__name__)

class VideoProcessor:
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
        logger.info(f"Initialized VideoProcessor with temp directory: {self.temp_dir}")

    async def burn_subtitles(
        self,
        video_url: str,
        subtitle_url: str,
        video_uuid: str,
        language: str
    ) -> Optional[str]:
        """
        Burns subtitles into a video using FFmpeg.
        
        Args:
            video_url: URL of the source video
            subtitle_url: URL of the SRT subtitle file
            video_uuid: UUID of the video
            language: Language code of the subtitles
            
        Returns:
            URL of the processed video with burned subtitles, or None if failed
        """
        temp_video = None
        temp_subtitle = None
        temp_output = None
        
        try:
            # Create temporary files
            temp_video = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
            temp_subtitle = tempfile.NamedTemporaryFile(delete=False, suffix='.srt')
            temp_output = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
            
            # Extract file paths from URLs
            video_path = video_url.split(f"{settings.STORAGE_BUCKET}/")[-1]
            subtitle_path = subtitle_url.split(f"{settings.STORAGE_BUCKET}/")[-1]
            
            logger.info(f"Processing video: {video_path}")
            logger.info(f"With subtitles: {subtitle_path}")
            
            # Download files
            if not download_file(video_path, temp_video.name):
                raise Exception("Failed to download video file")
            if not download_file(subtitle_path, temp_subtitle.name):
                raise Exception("Failed to download subtitle file")
            
            # Prepare FFmpeg command
            try:
                # Get video metadata
                probe = ffmpeg.probe(temp_video.name)
                video_info = next(s for s in probe['streams'] if s['codec_type'] == 'video')
                width = int(video_info['width'])
                height = int(video_info['height'])
                
                # Calculate font size based on video resolution
                # Using an ultra-minimal ratio (1/32) for extremely subtle subtitles
                # For 1080p (1920x1080) this will result in ~34px font
                # For 720p (1280x720) this will result in ~22px font
                font_size = min(height // 32, 18)  # Cap at 18px for ultra-minimal look
                
                # Build FFmpeg command
                stream = ffmpeg.input(temp_video.name)
                
                # Add subtitles with ultra-minimal styling
                # - Ultra small, extra light font
                # - Very thin white text with minimal outline
                # - Extra tight line spacing
                # - Subtle positioning near bottom
                stream = ffmpeg.filter(
                    stream,
                    'subtitles',
                    temp_subtitle.name,
                    force_style=(
                        f'FontName=Arial,'
                        f'FontSize={font_size},'
                        f'Bold=0,'                 # Normal weight
                        f'PrimaryColour=&HFFFFFF,'  # White text
                        f'OutlineColour=&H000000,'  # Black outline
                        f'Outline=0.6,'            # Very thin outline
                        f'Shadow=0.3,'             # Minimal shadow
                        f'MarginV=20,'             # Closer to bottom
                        f'Spacing=0.5,'            # Extra tight letter spacing
                        f'LineSpacing=0.6,'        # Minimal space between lines
                        f'Alignment=2,'            # Centered
                        f'BorderStyle=1'           # Outline only, no background box
                    )
                )
                
                # Output with same codec settings
                stream = ffmpeg.output(
                    stream,
                    temp_output.name,
                    acodec='copy',  # Copy audio codec without re-encoding
                    vcodec='libx264',  # Use H.264 for video
                    preset='medium',  # Balance between speed and quality
                    crf=23,  # Constant Rate Factor for quality
                    map='0:a?',  # Map all audio streams if they exist
                    strict='-2'  # Allow experimental codecs
                )
                
                # Run FFmpeg command with detailed logging
                try:
                    ffmpeg.run(
                        stream,
                        capture_stdout=True,
                        capture_stderr=True,
                        overwrite_output=True
                    )
                    logger.info("FFmpeg processing completed successfully")
                except ffmpeg.Error as e:
                    stderr = e.stderr.decode() if e.stderr else "Unknown error"
                    logger.error(f"FFmpeg error: {stderr}")
                    raise Exception(f"Failed to process video: {stderr}")
                
            except ffmpeg.Error as e:
                logger.error(f"FFmpeg error: {str(e.stderr.decode() if e.stderr else 'Unknown error')}")
                raise Exception(f"Failed to process video: {str(e)}")
            
            # Generate output path
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"{timestamp}_{video_uuid[:8]}_subtitled_{language}.mp4"
            output_path = f"processed_videos/{output_filename}"
            
            # Upload processed video
            with open(temp_output.name, 'rb') as f:
                if not upload_file(output_path, f.read(), 'video/mp4'):
                    raise Exception("Failed to upload processed video")
            
            # Generate and return the public URL
            processed_url = get_file_url(output_path)
            logger.info(f"Successfully processed video: {processed_url}")
            return processed_url
            
        except Exception as e:
            logger.error(f"Error processing video: {str(e)}")
            return None
            
        finally:
            # Clean up temporary files
            for temp_file in [temp_video, temp_subtitle, temp_output]:
                if temp_file and os.path.exists(temp_file.name):
                    try:
                        os.unlink(temp_file.name)
                    except Exception as e:
                        logger.error(f"Error cleaning up temporary file: {str(e)}")
            
            if os.path.exists(self.temp_dir):
                try:
                    os.rmdir(self.temp_dir)
                except Exception as e:
                    logger.error(f"Error cleaning up temp directory: {str(e)}")

    def __del__(self):
        """Cleanup temporary directory on object destruction."""
        if os.path.exists(self.temp_dir):
            try:
                os.rmdir(self.temp_dir)
            except Exception as e:
                logger.error(f"Error cleaning up temp directory in destructor: {str(e)}")

# Create a singleton instance
video_processor = VideoProcessor() 