import asyncio
import json
import time
from httpx import AsyncClient, TimeoutException, Timeout
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_dubbing_flow():
    # Configuration
    BASE_URL = "http://localhost:8000/api/v1"
    VIDEO_UUID = "d7ddbfd0-2fc3-4f80-b363-6f45332dc35d"
    VIDEO_URL = "https://umkrrnuzoplzqyojbsnj.supabase.co/storage/v1/object/public/video-analyzer/videos/20250130_163549_d7ddbfd0.mp4"
    ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJyZWhhbi5hbGlAd29ya2h1Yi5haSIsImV4cCI6MTczOTYxMTM5NH0.F4Tjsa6FDeccAj2Es3WzXB7gb8-JOBfG9juTgc8bJc4"
    
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    
    # Configure timeout
    timeout = Timeout(60.0)
    
    async with AsyncClient(timeout=timeout) as client:
        try:
            # Step 1: Generate subtitles with dubbing enabled
            logger.info("Step 1: Initiating subtitle generation with dubbing...")
            subtitle_request = {
                "language": "es",  # Spanish dubbing
                "enable_dubbing": True
            }
            
            logger.info(f"Making request to: {BASE_URL}/videos/{VIDEO_UUID}/generate_subtitles")
            logger.info(f"Headers: {headers}")
            logger.info(f"Request body: {json.dumps(subtitle_request, indent=2)}")
            
            response = await client.post(
                f"{BASE_URL}/videos/{VIDEO_UUID}/generate_subtitles",
                json=subtitle_request,
                headers=headers
            )
            
            if response.status_code != 200:
                logger.error(f"Error response: {response.text}")
                response.raise_for_status()
            
            result = response.json()
            logger.info(f"Initial response: {json.dumps(result, indent=2)}")
            
            if not result.get("dubbing_id"):
                raise Exception("No dubbing_id received in response")
            
            dubbing_id = result["dubbing_id"]
            logger.info(f"Dubbing job created with ID: {dubbing_id}")
            
            # Step 2: Poll the dubbing status until completion
            logger.info("Step 2: Polling dubbing status...")
            max_attempts = 30  # Maximum polling attempts (5 minutes total)
            poll_interval = 10  # Seconds between polling attempts
            
            for attempt in range(max_attempts):
                try:
                    response = await client.get(
                        f"{BASE_URL}/videos/{VIDEO_UUID}/dubbing/{dubbing_id}",
                        headers=headers
                    )
                    response.raise_for_status()
                    status_result = response.json()
                    
                    status = status_result.get("status", "").lower()
                    logger.info(f"Attempt {attempt + 1}: Status = {status}")
                    logger.info(f"Response: {json.dumps(status_result, indent=2)}")
                    
                    if status == "completed":
                        logger.info("Dubbing completed successfully!")
                        logger.info(f"Dubbed video URL: {status_result.get('dubbed_video_url')}")
                        break
                    elif status == "failed":
                        raise Exception(f"Dubbing process failed: {status_result.get('detail', 'No error details')}")
                    
                    if attempt < max_attempts - 1:
                        logger.info(f"Waiting {poll_interval} seconds before next check...")
                        await asyncio.sleep(poll_interval)
                except Exception as e:
                    logger.error(f"Error during polling attempt {attempt + 1}: {str(e)}")
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(poll_interval)
                    else:
                        raise
            else:
                raise Exception("Maximum polling attempts reached without completion")
            
            logger.info("Test completed successfully!")
            
        except Exception as e:
            logger.error(f"Test failed: {str(e)}")
            raise

if __name__ == "__main__":
    asyncio.run(test_dubbing_flow()) 