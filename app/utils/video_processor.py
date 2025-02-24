import ffmpeg
import tempfile
import os
import logging
from datetime import datetime
from typing import Optional, Tuple
from app.core.config import settings
from app.utils.s3 import upload_file, download_file, get_file_url
from app.utils.database import get_video_by_uuid
from app.models.models import SubtitleStyles
import json

logger = logging.getLogger(__name__)

class VideoProcessor:
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
        logger.info(f"Initialized VideoProcessor with temp directory: {self.temp_dir}")

    def _convert_color_to_ass(self, hex_color: str) -> str:
        """
        Convert HTML hex color (#RRGGBB) to ASS format (&HBBGGRR).
        ASS uses BGR format instead of RGB.
        """
        try:
            hex_color = hex_color.replace("#", "")
            r, g, b = hex_color[:2], hex_color[2:4], hex_color[4:]
            return f"&H{b}{g}{r}"
        except Exception as e:
            logger.error(f"Error converting color {hex_color}: {str(e)}")
            return "&HFFFFFF"  # Default to white on error

    def _get_alignment_value(self, position: str, alignment: str) -> int:
        """
        Calculate ASS alignment value based on position and alignment.
        ASS uses a numpad-style alignment system:
        7 8 9 (top)
        4 5 6 (middle)
        1 2 3 (bottom)
        """
        if position == "top":
            if alignment == "left":
                return 7
            elif alignment == "right":
                return 9
            else:  # center
                return 8
        else:  # bottom
            if alignment == "left":
                return 1
            elif alignment == "right":
                return 3
            else:  # center
                return 2

    def _get_font_size_multiplier(self, size_setting: str) -> float:
        """Get font size multiplier based on size setting."""
        font_sizes = {
            "large": 32,
            "medium": 24,
            "small": 16
        }
        return font_sizes.get(size_setting.lower(), 16)  # Default to small (16px) if unknown

    def _get_font_for_language(self, font_family: str, language: str) -> str:
        """Get appropriate font based on language and user preference."""
        language_fonts = {
            "zh": "Noto Sans CJK SC",
            "ja": "Noto Sans CJK JP",
            "ko": "Noto Sans CJK KR"
        }
        return language_fonts.get(language, font_family)

    def _convert_styles_to_ass(self, subtitle_styles: dict, base_font_size: int, language: str) -> str:
        """
        Convert subtitle styles to ASS format string.
        
        Args:
            subtitle_styles: Dictionary containing subtitle style properties:
                - fontSize: "small", "medium", "large"
                - fontWeight: "normal", "bold"
                - fontStyle: "normal", "italic"
                - color: hex color string
                - position: "top", "bottom"
                - alignment: "left", "center", "right"
            base_font_size: Base font size (not used)
            language: Language code for font selection
            
        Returns:
            ASS style string
        """
        try:
            # Font size handling - using fixed pixel sizes
            # If subtitle_styles is empty or None, use 24px as default and add outline/shadow
            if not subtitle_styles:
                base_font_size = 24
                final_font_size = round(base_font_size / 1.5, 2)
                print("[DEBUG] No custom styles found, using default font size: 24px with outline/shadow")
                outline_shadow = "1,1"  # Use outline and shadow when no custom styles
            else:
                font_size_setting = str(subtitle_styles.get("fontSize", "small")).lower()
                base_font_size = self._get_font_size_multiplier(font_size_setting)
                final_font_size = round(base_font_size / 1.5, 2)
                print(f"[DEBUG] Using custom font size: {font_size_setting} -> {final_font_size}px without outline/shadow")
                outline_shadow = "0,0"  # No outline and shadow when custom styles are present
            
            # Color handling - convert from #RRGGBB to &HBBGGRR
            primary_color = self._convert_color_to_ass(subtitle_styles.get("color", "#FFFFFF"))
            primary_with_alpha = f"&H00{primary_color[2:]}"  # Full opacity for text
            transparent = "&H00000000"  # Fully transparent background
            
            # Position and alignment
            position = str(subtitle_styles.get("position", "bottom")).lower()
            alignment = str(subtitle_styles.get("alignment", "center")).lower()
            alignment_value = self._get_alignment_value(position, alignment)
            
            # Font style
            font_weight = str(subtitle_styles.get("fontWeight", "normal")).lower()
            font_style = str(subtitle_styles.get("fontStyle", "normal")).lower()
            
            # Calculate margins (fixed values)
            margin_v = 30 if position == "top" else 40
            margin_h = 20
            
            # Build the complete ASS style string
            style_string = (
                f'[Script Info]\n'
                f'ScriptType: v4.00+\n'
                f'PlayResX: 384\n'
                f'PlayResY: 288\n\n'
                f'[V4+ Styles]\n'
                f'Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n'
                f'Style: Default,Arial,{final_font_size},{primary_with_alpha},{transparent},{transparent},{transparent},'
                f'{1 if font_weight == "bold" else 0},'  # Bold
                f'{1 if font_style == "italic" else 0},'  # Italic
                f'0,0,'  # Underline, StrikeOut
                f'100,100,'  # ScaleX, ScaleY
                f'0,0,'  # Spacing, Angle
                f'1,'  # BorderStyle (1 for normal outline)
                f'{outline_shadow},'  # Outline and Shadow (1,1 for no styles, 0,0 for custom styles)
                f'{alignment_value},'  # Alignment
                f'{margin_h},{margin_h},{margin_v},'  # MarginL, MarginR, MarginV
                f'1\n\n'  # Encoding
                f'[Events]\n'
                f'Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n'
            )
            
            logger.info(f"Generated ASS style string: {style_string}")
            return style_string
            
        except Exception as e:
            logger.error(f"Error converting styles to ASS: {str(e)}")
            # Return default style string on error - use outline/shadow since this is a fallback
            return (
                '[Script Info]\n'
                'ScriptType: v4.00+\n'
                'PlayResX: 384\n'
                'PlayResY: 288\n\n'
                '[V4+ Styles]\n'
                'Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n'
                'Style: Default,Arial,24,&H00FFFFFF,&H00000000,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,1,1,2,20,20,40,1\n\n'  # Using outline/shadow 1,1 for fallback
                '[Events]\n'
                'Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n'
            )

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
        temp_ass = None
        temp_styled_ass = None
        
        try:
            # Create temporary files
            temp_video = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
            temp_subtitle = tempfile.NamedTemporaryFile(delete=False, suffix='.srt')
            temp_ass = tempfile.NamedTemporaryFile(delete=False, suffix='.ass')
            temp_styled_ass = tempfile.NamedTemporaryFile(delete=False, suffix='.ass')
            temp_output = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
            
            # Extract file paths from URLs
            video_path = video_url.split(f"{settings.STORAGE_BUCKET}/")[-1]
            subtitle_path = subtitle_url.split(f"{settings.STORAGE_BUCKET}/")[-1]
            
            print(f"[DEBUG] Processing video: {video_path}")
            print(f"[DEBUG] With subtitles: {subtitle_path}")
            
            # Download files
            if not download_file(video_path, temp_video.name):
                raise Exception("Failed to download video file")
            if not download_file(subtitle_path, temp_subtitle.name):
                raise Exception("Failed to download subtitle file")
            
            try:
                # Get video metadata
                probe = ffmpeg.probe(temp_video.name)
                video_info = next(s for s in probe['streams'] if s['codec_type'] == 'video')
                width = int(video_info['width'])
                height = int(video_info['height'])
                
                print(f"[DEBUG] Video dimensions: {width}x{height}")
                
                # Calculate base font size based on video resolution
                base_font_size = min(height // 32, 18)  # Cap at 18px for ultra-minimal look
                print(f"[DEBUG] Base font size calculated: {base_font_size}")
                
                # Get video details and handle subtitle styles
                video = await get_video_by_uuid(video_uuid)
                if not video:
                    print("[WARNING] Video not found, using default styles")
                    subtitle_styles = {}
                else:
                    # Get subtitle styles, ensuring we have a dict
                    subtitle_styles = video.get("subtitle_styles", {})
                    print(f"[DEBUG] Retrieved subtitle styles from DB: {subtitle_styles}")
                    
                    if subtitle_styles is None:
                        subtitle_styles = {}
                    elif isinstance(subtitle_styles, str):
                        try:
                            subtitle_styles = json.loads(subtitle_styles)
                        except json.JSONDecodeError:
                            print("[WARNING] Failed to parse subtitle styles JSON")
                            subtitle_styles = {}
                
                print(f"[DEBUG] Using subtitle styles: {subtitle_styles}")
                
                # Step 1: Convert SRT to basic ASS
                print("[DEBUG] Converting SRT to ASS format...")
                ffmpeg.input(temp_subtitle.name, sub_charenc='UTF-8').output(
                    temp_ass.name,
                    f='ass',
                    **{'loglevel': 'error'}
                ).overwrite_output().run(capture_stdout=True, capture_stderr=True)
                
                # Step 2: Read the converted ASS file
                with open(temp_ass.name, 'r', encoding='utf-8') as f:
                    ass_content = f.read()
                
                # Step 3: Generate our style string
                style_string = self._convert_styles_to_ass(subtitle_styles, base_font_size, language)
                
                # Step 4: Replace the [V4+ Styles] section in the ASS file
                style_section_start = ass_content.find('[V4+ Styles]')
                events_section_start = ass_content.find('[Events]')
                
                if style_section_start != -1 and events_section_start != -1:
                    # Extract the [Events] section and everything after it
                    events_section = ass_content[events_section_start:]
                    
                    # Combine our style string with the events section
                    final_ass_content = style_string + events_section
                    
                    # Write the final ASS file
                    with open(temp_styled_ass.name, 'w', encoding='utf-8') as f:
                        f.write(final_ass_content)
                    
                    print("[DEBUG] Successfully created styled ASS file")
                else:
                    print("[WARNING] Could not find style or events section in ASS file")
                    raise Exception("Invalid ASS file structure")
                
                # Step 5: Create FFmpeg stream with styled ASS subtitles
                print("[DEBUG] Creating FFmpeg stream with styled subtitles...")
                stream = ffmpeg.input(temp_video.name)
                
                # Apply subtitle filter using the styled ASS file
                stream = ffmpeg.filter(
                    stream,
                    'ass',
                    temp_styled_ass.name
                )
                
                # Output with same codec settings
                stream = ffmpeg.output(
                    stream,
                    temp_output.name,
                    acodec='copy',
                    vcodec='libx264',
                    preset='medium',
                    crf=23,
                    map='0:a?',
                    strict='-2'
                )
                
                # Run FFmpeg command
                print("[DEBUG] Running FFmpeg command...")
                ffmpeg.run(
                    stream,
                    capture_stdout=True,
                    capture_stderr=True,
                    overwrite_output=True
                )
                print("[DEBUG] FFmpeg processing completed successfully")
                
            except ffmpeg.Error as e:
                stderr = e.stderr.decode() if e.stderr else "Unknown error"
                print(f"[ERROR] FFmpeg error: {stderr}")
                raise Exception(f"Failed to process video: {stderr}")
            
            # Generate output path
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"{timestamp}_{video_uuid[:8]}_subtitled_{language}.mp4"
            output_path = f"processed_videos/{output_filename}"
            
            # Upload processed video
            print("[DEBUG] Uploading processed video...")
            with open(temp_output.name, 'rb') as f:
                if not upload_file(output_path, f.read(), 'video/mp4'):
                    raise Exception("Failed to upload processed video")
            
            # Generate and return the public URL
            processed_url = get_file_url(output_path)
            print(f"[DEBUG] Successfully processed video: {processed_url}")
            return processed_url
            
        except Exception as e:
            print(f"[ERROR] Error processing video: {str(e)}")
            logger.error(f"Error processing video: {str(e)}")
            return None
            
        finally:
            # Clean up temporary files
            for temp_file in [temp_video, temp_subtitle, temp_output, temp_ass, temp_styled_ass]:
                if temp_file and os.path.exists(temp_file.name):
                    try:
                        os.unlink(temp_file.name)
                    except Exception as e:
                        print(f"[ERROR] Error cleaning up temporary file: {str(e)}")
            
            if os.path.exists(self.temp_dir):
                try:
                    os.rmdir(self.temp_dir)
                except Exception as e:
                    print(f"[ERROR] Error cleaning up temp directory: {str(e)}")

    def __del__(self):
        """Cleanup temporary directory on object destruction."""
        if os.path.exists(self.temp_dir):
            try:
                os.rmdir(self.temp_dir)
            except Exception as e:
                logger.error(f"Error cleaning up temp directory in destructor: {str(e)}")

# Create a singleton instance
video_processor = VideoProcessor() 