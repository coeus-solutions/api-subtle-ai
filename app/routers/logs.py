from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app.routers.auth import get_current_user
from app.models.models import Log

router = APIRouter()

@router.get("/")
async def get_activity_logs(current_user: dict = Depends(get_current_user)):
    # TODO: Implement fetching logs from Supabase
    return {
        "logs": []
    }

async def log_activity(user_id: int, action: str):
    """
    Utility function to log user activities
    """
    log = Log(
        user_id=user_id,
        action=action
    )
    # TODO: Save log to Supabase
    return log 