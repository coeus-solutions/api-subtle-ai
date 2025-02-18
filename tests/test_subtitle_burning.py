import asyncio
import logging
from app.utils.video_processor import video_processor

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_subtitle_burning():
    """Test the subtitle burning functionality directly."""
    try:
        # Test parameters
        video_url = "https://umkrrnuzoplzqyojbsnj.supabase.co/storage/v1/object/public/video-analyzer/videos/20250217_083739_2103f3c9.mp4"
        subtitle_url = "https://umkrrnuzoplzqyojbsnj.supabase.co/storage/v1/object/public/video-analyzer/subtitles/20250217_083808_2103f3c9_de.srt"
        video_uuid = "2103f3c9-d2f3-42d3-8abb-6f7b036d1e82"
        language = "de"

        logger.info("Starting subtitle burning test...")
        logger.info(f"Video URL: {video_url}")
        logger.info(f"Subtitle URL: {subtitle_url}")
        logger.info(f"Video UUID: {video_uuid}")
        logger.info(f"Language: {language}")

        # Call the burn_subtitles function
        result = await video_processor.burn_subtitles(
            video_url=video_url,
            subtitle_url=subtitle_url,
            video_uuid=video_uuid,
            language=language
        )

        if result:
            logger.info("✅ Subtitle burning successful!")
            logger.info(f"Processed video URL: {result}")
        else:
            logger.error("❌ Subtitle burning failed!")
            raise Exception("Failed to burn subtitles into video")

    except Exception as e:
        logger.error(f"❌ Test failed with error: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(test_subtitle_burning()) 