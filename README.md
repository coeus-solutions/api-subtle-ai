# Video Analyzer API

A FastAPI backend system for video analysis and subtitle generation using AI.

## Features

- User authentication with JWT
- Video upload and management
- AI-powered subtitle generation using OpenAI's Whisper
- Activity logging
- Secure file storage using Supabase

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
- POST `/api/v1/videos`: Upload a video
- GET `/api/v1/videos`: List all videos
- DELETE `/api/v1/videos/{video_uuid}`: Delete a video
- POST `/api/v1/videos/{video_uuid}/generate_subtitles`: Generate subtitles for a video

### Subtitles
- GET `/api/v1/subtitles`: List all subtitles
- GET `/api/v1/subtitles/{subtitle_uuid}`: Download a subtitle file

### Logs
- GET `/api/v1/logs`: Get activity logs

## Database Schema

The application uses Supabase with the following tables:

1. Users
   - id (int, primary key)
   - uuid (uuid)
   - email (string, unique)
   - password_hash (string)
   - created_at (timestamp)
   - updated_at (timestamp)

2. Videos
   - id (int, primary key)
   - uuid (uuid)
   - user_id (int, foreign key)
   - video_url (string)
   - status (string)
   - created_at (timestamp)
   - updated_at (timestamp)

3. Subtitles
   - id (int, primary key)
   - uuid (uuid)
   - video_id (int, foreign key)
   - subtitle_url (string)
   - format (string)
   - created_at (timestamp)
   - updated_at (timestamp)

4. Logs
   - id (int, primary key)
   - uuid (uuid)
   - user_id (int, foreign key)
   - action (string)
   - created_at (timestamp)

## Security

- JWT-based authentication
- Password hashing using bcrypt
- Input validation and sanitization
- Protected API endpoints
- Secure file storage

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request 