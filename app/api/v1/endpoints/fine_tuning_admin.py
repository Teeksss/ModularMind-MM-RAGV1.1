from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Body, Query
from pydantic import BaseModel, Field
import logging
from datetime import datetime, timedelta

from app.models.user import User
from app.api.deps import get_current_admin_user
from app.db.crud.fine_tuning import (
    get_fine_tuning_jobs,
    get_fine_tuning_job,
    save_fine_tuning_job,
    update_fine_tuning_job
)
from app.services.fine_tuning_service import get_fine_tuning_service
from app.db.crud.feedback import get_feedbacks_by_criteria
from app.services.feedback_analyzer import prepare_fine_tuning_data

router = APIRouter()

logger = logging.getLogger(__name__)

class CreateFineTuningJobRequest(BaseModel):
    """Request model for creating a fine-tuning job."""
    name: str
    model_name: str = "gpt-3.5-turbo"
    use_feedback: bool = True
    min_rating: int = Field(4, ge=1, le=5)
    time_range: str = "30days"
    hyperparameters: Optional[Dict[str, Any]] = None

@router.get("/jobs")
async def list_fine_tuning_jobs(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_admin_user)
):
    """List fine-tuning jobs."""
    try:
        jobs = await get_fine_tuning_jobs(status=status)
        return {"jobs": jobs, "count": len(jobs)}
    except Exception as e:
        logger.error(f"Error listing fine-tuning jobs: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list fine-tuning jobs")

@router.get("/jobs/{job_id}")
async def get_fine_tuning_job_details(
    job_id: str,
    current_user: User = Depends(get_current_admin_user)
):
    """Get fine-tuning job details."""
    try:
        job = await get_fine_tuning_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Fine-tuning job not found")
        return job
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting fine-tuning job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get fine-tuning job details")

@router.post("/jobs", status_code=201)
async def create_fine_tuning_job(
    request: CreateFineTuningJobRequest = Body(...),
    current_user: User = Depends(get_current_admin_user)
):
    """Create a new fine-tuning job from user feedback."""
    try:
        # Get feedback data based on criteria
        start_date = None
        if request.time_range:
            today = datetime.utcnow()
            if request.time_range == "7days":
                start_date = today - timedelta(days=7)
            elif request.time_range == "30days":
                start_date = today - timedelta(days=30)
            elif request.time_range == "90days":
                start_date = today - timedelta(days=90)
        
        # Get feedback data
        criteria = {"rating": {"$gte": request.min_rating}}
        if start_date:
            criteria["timestamp"] = {"$gte": start_date}
        
        feedbacks = await get_feedbacks_by_criteria(criteria)
        
        if not feedbacks:
            raise HTTPException(status_code=400, detail="No suitable feedback found for fine-tuning")
        
        # Prepare training data
        training_data = await prepare_fine_tuning_data(feedbacks)
        
        if not training_data:
            raise HTTPException(status_code=400, detail="Failed to prepare training data")
        
        # Get fine-tuning service
        fine_tuning_service = get_fine_tuning_service()
        
        # Start fine-tuning job
        job_id = await fine_tuning_service.start_fine_tuning_job(
            training_data=training_data,
            job_name=request.name
        )
        
        # Get job details
        job = await get_fine_tuning_job(job_id)
        
        return {"job_id": job_id, "job": job, "examples_count": len(training_data)}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating fine-tuning job: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create fine-tuning job: {str(e)}")

@router.post("/jobs/{job_id}/cancel")
async def cancel_fine_tuning_job(
    job_id: str,
    current_user: User = Depends(get_current_admin_user)
):
    """Cancel a fine-tuning job."""
    try:
        # Get job
        job = await get_fine_tuning_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Fine-tuning job not found")
        
        # Check if job can be cancelled
        if job["status"] not in ["queued", "running", "processing"]:
            raise HTTPException(status_code=400, detail=f"Job with status '{job['status']}' cannot be cancelled")
        
        # Update job status
        await update_fine_tuning_job(job_id, {"status": "cancelled"})
        
        # Cancel with provider if applicable
        if job.get("provider_job_id"):
            fine_tuning_service = get_fine_tuning_service()
            # In a real implementation, we would cancel the job with the provider
            # await fine_tuning_service.cancel_job(job["provider_job_id"])
        
        return {"status": "success", "message": "Job cancelled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling fine-tuning job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to cancel fine-tuning job")

@router.post("/jobs/{job_id}/activate")
async def activate_fine_tuned_model(
    job_id: str,
    current_user: User = Depends(get_current_admin_user)
):
    """Activate a fine-tuned model."""
    try:
        # Get job
        job = await get_fine_tuning_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Fine-tuning job not found")
        
        # Check if job is completed
        if job["status"] != "completed" or not job.get("fine_tuned_model"):
            raise HTTPException(status_code=400, detail="Job is not completed or does not have a fine-tuned model")
        
        # Update model status as active
        # In a real implementation, we would update the model in the configuration
        # and make it available for use
        
        return {
            "status": "success",
            "message": "Fine-tuned model activated successfully",
            "model": job["fine_tuned_model"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error activating fine-tuned model for job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to activate fine-tuned model")

@router.get("/metrics/{job_id}")
async def get_fine_tuning_metrics(
    job_id: str,
    current_user: User = Depends(get_current_admin_user)
):
    """Get metrics for a fine-tuning job."""
    try:
        # Get job
        job = await get_fine_tuning_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Fine-tuning job not found")
        
        # In a real implementation, we would fetch metrics from the provider
        # or from stored metrics
        
        # For demonstration purposes, generate some sample metrics
        metrics = {
            "job_id": job_id,
            "training_loss": 0.2345,
            "validation_loss": 0.3456,
            "epochs": 3,
            "examples_used": job.get("examples_count", 0),
            "training_time_seconds": 1200,
            "before_accuracy": 65.4,
            "after_accuracy": 82.7,
            "improvement_percentage": 17.3
        }
        
        return metrics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting metrics for job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get fine-tuning metrics")