from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel, Field
import logging
from datetime import datetime

from app.models.user import User
from app.api.deps import get_current_user
from app.db.crud.feedback import save_feedback, get_feedbacks_by_query
from app.services.feedback_analyzer import analyze_feedback

router = APIRouter()

logger = logging.getLogger(__name__)

class FeedbackItem(BaseModel):
    """Model for user feedback on responses."""
    response_id: str
    query_id: str
    rating: int = Field(..., ge=1, le=5, description="User rating from 1-5")
    helpful: Optional[bool] = None
    feedback_text: Optional[str] = None
    selected_sources: Optional[List[str]] = None
    missing_information: Optional[bool] = None
    tags: Optional[List[str]] = []
    context: Optional[Dict[str, Any]] = {}

@router.post("/submit", status_code=201)
async def submit_feedback(
    feedback: FeedbackItem = Body(...),
    current_user: User = Depends(get_current_user)
):
    """Submit feedback for a response."""
    try:
        # Add user information and timestamp
        feedback_data = feedback.dict()
        feedback_data["user_id"] = current_user.id
        feedback_data["timestamp"] = datetime.utcnow()
        
        # Save feedback to database
        feedback_id = await save_feedback(feedback_data)
        
        # Run asynchronous feedback analysis
        await analyze_feedback(feedback_data)
        
        return {"status": "success", "feedback_id": feedback_id}
    
    except Exception as e:
        logger.error(f"Error submitting feedback: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to submit feedback")

@router.get("/stats")
async def get_feedback_stats(
    query_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get aggregated feedback statistics."""
    try:
        # Get feedbacks matching criteria
        feedbacks = await get_feedbacks_by_query(
            query_id=query_id,
            start_date=start_date,
            end_date=end_date
        )
        
        # Calculate statistics
        total_count = len(feedbacks)
        if total_count == 0:
            return {
                "total_count": 0,
                "average_rating": 0,
                "helpful_percentage": 0,
                "top_tags": []
            }
            
        # Calculate average rating
        average_rating = sum(f["rating"] for f in feedbacks) / total_count
        
        # Calculate helpful percentage
        helpful_feedbacks = [f for f in feedbacks if f.get("helpful") is True]
        helpful_percentage = (len(helpful_feedbacks) / total_count) * 100
        
        # Count tags
        tags_count = {}
        for feedback in feedbacks:
            for tag in feedback.get("tags", []):
                tags_count[tag] = tags_count.get(tag, 0) + 1
                
        # Get top 5 tags
        top_tags = sorted(tags_count.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "total_count": total_count,
            "average_rating": round(average_rating, 2),
            "helpful_percentage": round(helpful_percentage, 2),
            "top_tags": [{"tag": tag, "count": count} for tag, count in top_tags]
        }
        
    except Exception as e:
        logger.error(f"Error getting feedback stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get feedback statistics")