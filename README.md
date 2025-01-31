# SubtleAI API

A FastAPI backend system for AI-powered video subtitle generation and management.

## Features

- User authentication with JWT
- Video upload and management
- AI-powered subtitle generation using OpenAI's Whisper
- Multi-language subtitle support (English, German, Spanish, French, Japanese)
- Secure file storage using Supabase
- Usage tracking and free tier management (50 free minutes)

## Prerequisites

- Python 3.8+
- Supabase account
- OpenAI API key

## Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd api-video-analyzer
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create `.env` file:
```bash
cp .env.example .env
```

5. Update the `.env` file with your credentials:
- Add your Supabase URL and key
- Add your OpenAI API key
- Update JWT secret key

## Running the Application

1. Start the FastAPI server:
```bash
uvicorn main:app --reload
```

2. Access the API documentation:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

### Authentication
- POST `/api/v1/auth/register`: Register a new user
- POST `/api/v1/auth/login`: Login and get JWT token

### Videos
- POST `/api/v1/videos/upload`: Upload a video (supports MP4, WebM, WAV)
- GET `/api/v1/videos`: List all videos
- DELETE `/api/v1/videos/{video_uuid}`: Delete a video and its subtitles
- POST `/api/v1/videos/{video_uuid}/generate_subtitles`: Generate subtitles for a video

### Subtitles
- GET `/api/v1/subtitles`: List all subtitles
- GET `/api/v1/subtitles/{subtitle_uuid}`: Download a subtitle file

### Users
- GET `/api/v1/users/me`: Get current user details and usage statistics

## Database Schema

The application uses Supabase with the following tables:

1. Users
   - id (int, primary key)
   - uuid (uuid)
   - email (string, unique)
   - password_hash (string)
   - minutes_consumed (decimal)
   - free_minutes_used (decimal)
   - total_cost (decimal)
   - created_at (timestamp)
   - updated_at (timestamp)

2. Videos
   - id (int, primary key)
   - uuid (uuid)
   - user_id (int, foreign key)
   - video_url (string)
   - original_name (string)
   - duration_minutes (decimal)
   - status (string)
   - created_at (timestamp)
   - updated_at (timestamp)

3. Subtitles
   - id (int, primary key)
   - uuid (uuid)
   - video_id (int, foreign key)
   - subtitle_url (string)
   - format (string)
   - language (string)
   - created_at (timestamp)
   - updated_at (timestamp)

## File Restrictions

- Supported formats: MP4, WebM, WAV
- Maximum file size: 20MB
- Maximum video duration: 60 minutes

## Pricing

- First 50 minutes of video processing are free
- After free tier: $0.10 per minute
- Cost is calculated based on video duration

## Security

- JWT-based authentication
- Password hashing using bcrypt
- Input validation and sanitization
- Protected API endpoints
- Secure file storage with Supabase

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request 