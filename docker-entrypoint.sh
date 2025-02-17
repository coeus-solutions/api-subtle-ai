#!/bin/bash
set -e

if [ "$APP_ENV" = "dev" ]; then
    echo "Starting application in development mode..."
    exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload --log-level info
else
    echo "Starting application in production mode..."
    exec uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
fi 