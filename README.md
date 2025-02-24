# SubtleAI - AI-Powered Video Subtitle Generator

SubtleAI is a powerful API service that generates, translates, and burns subtitles into videos using advanced AI technologies.

## Features

### 1. Video Processing
- Upload videos up to 20MB in size
- Maximum video duration: 60 minutes
- Supported formats: MP4, WebM, WAV
- Automatic language detection for source audio

### 2. Subtitle Generation
- High-accuracy transcription using OpenAI Whisper
- Multiple language support:
  - English (en)
  - German (de)
  - Spanish (es)
  - French (fr)
  - Japanese (ja)
  - Russian (ru)
  - Italian (it)
  - Chinese (zh)
  - Turkish (tr)
  - Korean (ko)
  - Portuguese (pt)

### 3. Subtitle Customization
- Font size options: small, medium, large
- Font styles: normal, bold, italic
- Custom colors with hex color codes
- Position options: top, bottom
- Alignment options: left, center, right
- Optional outline and shadow effects

### 4. Video Dubbing
- AI-powered dubbing using ElevenLabs
- Natural-sounding voice synthesis
- Support for all available languages
- Automatic subtitle generation for dubbed audio

### 5. Subtitle Burning
- Permanent subtitle embedding into videos
- Support for custom styles
- Compatible with both original and dubbed videos
- High-quality output with FFmpeg processing

## Pricing

- First 30 minutes worth $37.50 are free
- $1.25 per minute after free tier
- Pricing includes:
  - Video processing
  - Subtitle generation
  - Translation
  - Dubbing (when enabled)
  - Subtitle burning

## Technical Details

### API Endpoints
- `/api/v1/videos/upload` - Upload new videos
- `/api/v1/videos/{video_uuid}/generate_subtitles` - Generate subtitles
- `/api/v1/videos/{video_uuid}/burn_subtitles` - Burn subtitles into video
- `/api/v1/videos/{video_uuid}/dubbing/{dubbing_id}/status` - Check dubbing status
- `/api/v1/videos/{video_uuid}/dubbing/{dubbing_id}/video` - Get dubbed video

### Authentication
- JWT-based authentication
- Token expiration: 3000 minutes
- Refresh tokens valid for 7 days

### Storage
- Supabase storage integration
- Automatic file management
- Secure URL generation

## Setup

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables (copy .env.example to .env):
```bash
cp .env.example .env
```

4. Run with Docker:
```bash
docker-compose up --build
```

## Development

### Requirements
- Python 3.11+
- FFmpeg
- Docker (optional)

### Environment Variables
Required environment variables are listed in `.env.example`. Make sure to set:
- Supabase credentials
- OpenAI API key
- ElevenLabs API key
- JWT configuration

## License
Proprietary software. All rights reserved. 