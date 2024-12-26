import openai
from app.core.config import settings

openai.api_key = settings.OPENAI_API_KEY

async def generate_subtitles_from_video(video_path: str, format: str = "srt"):
    """
    Generate subtitles from video using OpenAI's Whisper API
    """
    try:
        with open(video_path, "rb") as audio_file:
            transcript = await openai.Audio.transcribe(
                "whisper-1",
                audio_file,
                response_format=format
            )
        
        return {
            "success": True,
            "subtitles": transcript.text
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        } 