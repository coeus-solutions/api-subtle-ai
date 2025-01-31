from fastapi import APIRouter, Depends, HTTPException, status
from app.models.models import UserDetailsResponse
from app.routers.auth import get_current_user
from app.utils.database import get_user_details
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Create router with prefix and tags for Swagger documentation
router = APIRouter(
    prefix="/users",
    tags=["Users"],
    responses={
        401: {"description": "Authentication required"},
        404: {"description": "User not found"},
        500: {"description": "Internal server error"}
    }
)

@router.get(
    "/me",
    response_model=UserDetailsResponse,
    summary="Get Current User Details",
    description="""
    Get detailed information about the currently authenticated user including usage statistics.
    
    Returns:
    - User's email
    - Total minutes of video processed
    - Free minutes used (out of 50 minutes allocation)
    - Total cost incurred (after free minutes)
    - Remaining free minutes
    - Cost per minute ($0.10)
    - Free minutes allocation (50.0 minutes worth $5.00)
    - Account creation and last update timestamps
    
    Requires authentication via JWT token in Authorization header.
    """,
    responses={
        200: {
            "description": "User details retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "email": "user@example.com",
                        "minutes_consumed": 75.5,
                        "free_minutes_used": 50.0,
                        "total_cost": 2.55,
                        "minutes_remaining": 0.0,
                        "cost_per_minute": 0.10,
                        "free_minutes_allocation": 50.0,
                        "created_at": "2024-01-29T12:00:00Z",
                        "updated_at": "2024-01-29T12:00:00Z"
                    }
                }
            }
        }
    }
)
async def get_current_user_details(current_user: dict = Depends(get_current_user)):
    """Get detailed information about the current user including usage statistics."""
    try:
        user_details = await get_user_details(current_user["id"])
        if not user_details:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User details not found"
            )
        return user_details
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user details: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user details: {str(e)}"
        ) 