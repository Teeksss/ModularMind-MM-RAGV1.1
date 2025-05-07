import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from bson.objectid import ObjectId

from app.db.mongodb import get_database

logger = logging.getLogger(__name__)

async def save_feedback(feedback_data: Dict[str, Any]) -> str:
    """
    Save feedback to database.
    
    Args:
        feedback_data: The feedback data to save
        
    Returns:
        str: The ID of the saved feedback
    """
    db = await get_database()
    collection = db.feedback
    
    # Insert the feedback
    result = await collection.insert_one(feedback_data)
    
    return str(result.inserted_id)

async def get_feedbacks_by_query(
    query_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user_id: Optional[str] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Get feedbacks by query parameters.
    
    Args:
        query_id: Optional query ID to filter by
        start_date: Optional start date (ISO format)
        end_date: Optional end date (ISO format)
        user_id: Optional user ID to filter by
        limit: Maximum number of results to return
        
    Returns:
        List of feedback documents
    """
    db = await get_database()
    collection = db.feedback
    
    # Build query filter
    query_filter = {}
    
    if query_id:
        query_filter["query_id"] = query_id
        
    if user_id:
        query_filter["user_id"] = user_id
        
    # Date range filter
    date_filter = {}
    if start_date:
        try:
            start_datetime = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            date_filter["$gte"] = start_datetime
        except ValueError:
            logger.warning(f"Invalid start_date format: {start_date}")
    
    if end_date:
        try:
            end_datetime = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            date_filter["$lte"] = end_datetime
        except ValueError:
            logger.warning(f"Invalid end_date format: {end_date}")
    
    if date_filter:
        query_filter["timestamp"] = date_filter
    
    # Execute query
    cursor = collection.find(query_filter).limit(limit)
    
    # Convert to list of dictionaries
    results = await cursor.to_list(length=limit)
    
    # Convert ObjectId to string
    for result in results:
        if "_id" in result:
            result["id"] = str(result["_id"])
            del result["_id"]
    
    return results

async def get_feedback_by_id(feedback_id: str) -> Optional[Dict[str, Any]]:
    """
    Get feedback by ID.
    
    Args:
        feedback_id: The feedback ID
        
    Returns:
        The feedback document or None if not found
    """
    db = await get_database()
    collection = db.feedback
    
    try:
        # Convert string ID to ObjectId
        object_id = ObjectId(feedback_id)
        
        # Get feedback
        feedback = await collection.find_one({"_id": object_id})
        
        if feedback:
            # Convert ObjectId to string
            feedback["id"] = str(feedback["_id"])
            del feedback["_id"]
            
        return feedback
        
    except Exception as e:
        logger.error(f"Error getting feedback by ID: {str(e)}")
        return None

async def get_feedbacks_by_criteria(
    criteria: Dict[str, Any],
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Get feedbacks matching criteria.
    
    Args:
        criteria: Query criteria
        limit: Maximum number of results
        
    Returns:
        List of feedback documents
    """
    db = await get_database()
    collection = db.feedback
    
    # Execute query
    cursor = collection.find(criteria).limit(limit)
    
    # Convert to list of dictionaries
    results = await cursor.to_list(length=limit)
    
    # Convert ObjectId to string
    for result in results:
        if "_id" in result:
            result["id"] = str(result["_id"])
            del result["_id"]
    
    return results