import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from bson.objectid import ObjectId

from app.db.mongodb import get_database

logger = logging.getLogger(__name__)

async def save_fine_tuning_candidate(candidate_data: Dict[str, Any]) -> str:
    """
    Save a fine-tuning candidate to the database.
    
    Args:
        candidate_data: The candidate data to save
        
    Returns:
        str: The ID of the saved candidate
    """
    db = await get_database()
    collection = db.fine_tuning_candidates
    
    # Insert the candidate
    result = await collection.insert_one(candidate_data)
    
    return str(result.inserted_id)

async def get_fine_tuning_candidates(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    is_processed: Optional[bool] = None,
    limit: int = 1000
) -> List[Dict[str, Any]]:
    """
    Get fine-tuning candidates from the database.
    
    Args:
        start_date: Optional start date
        end_date: Optional end date
        is_processed: Optional processing status filter
        limit: Maximum number of results
        
    Returns:
        List of candidate documents
    """
    db = await get_database()
    collection = db.fine_tuning_candidates
    
    # Build query filter
    query_filter = {}
    
    # Date range filter
    date_filter = {}
    if start_date:
        date_filter["$gte"] = start_date
    
    if end_date:
        date_filter["$lte"] = end_date
    
    if date_filter:
        query_filter["timestamp"] = date_filter
        
    # Processing status filter
    if is_processed is not None:
        query_filter["is_processed"] = is_processed
    
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

async def mark_candidates_as_processed(candidate_ids: List[str]) -> int:
    """
    Mark candidates as processed.
    
    Args:
        candidate_ids: List of candidate IDs
        
    Returns:
        int: Number of updated documents
    """
    db = await get_database()
    collection = db.fine_tuning_candidates
    
    # Convert string IDs to ObjectIds
    object_ids = [ObjectId(cid) for cid in candidate_ids]
    
    # Update candidates
    result = await collection.update_many(
        {"_id": {"$in": object_ids}},
        {"$set": {"is_processed": True, "processed_at": datetime.utcnow()}}
    )
    
    return result.modified_count

async def save_fine_tuning_job(job_data: Dict[str, Any]) -> str:
    """
    Save a fine-tuning job to the database.
    
    Args:
        job_data: The job data to save
        
    Returns:
        str: The ID of the saved job
    """
    db = await get_database()
    collection = db.fine_tuning_jobs
    
    # Insert the job
    result = await collection.insert_one(job_data)
    
    return str(result.inserted_id)

async def update_fine_tuning_job(job_id: str, update_data: Dict[str, Any]) -> bool:
    """
    Update a fine-tuning job.
    
    Args:
        job_id: The job ID
        update_data: The data to update
        
    Returns:
        bool: Whether the update was successful
    """
    db = await get_database()
    collection = db.fine_tuning_jobs
    
    # Update job
    result = await collection.update_one(
        {"id": job_id},
        {"$set": update_data}
    )
    
    return result.modified_count > 0

async def get_fine_tuning_job(job_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a fine-tuning job by ID.
    
    Args:
        job_id: The job ID
        
    Returns:
        The job document or None if not found
    """
    db = await get_database()
    collection = db.fine_tuning_jobs
    
    # Get job
    job = await collection.find_one({"id": job_id})
    
    return job

async def get_fine_tuning_jobs(
    status: Optional[str] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Get fine-tuning jobs.
    
    Args:
        status: Optional status filter
        limit: Maximum number of results
        
    Returns:
        List of job documents
    """
    db = await get_database()
    collection = db.fine_tuning_jobs
    
    # Build query filter
    query_filter = {}
    
    if status:
        query_filter["status"] = status
    
    # Execute query
    cursor = collection.find(query_filter).sort("created_at", -1).limit(limit)
    
    # Convert to list of dictionaries
    results = await cursor.to_list(length=limit)
    
    return results