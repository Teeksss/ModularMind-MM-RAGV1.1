import asyncio
import logging
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
import uuid
import json
import os

from app.core.config import settings
from app.db.crud.fine_tuning import (
    get_fine_tuning_job,
    get_fine_tuning_jobs,
    get_fine_tuning_candidates,
    mark_candidates_as_processed,
    save_fine_tuning_job
)
from app.services.fine_tuning_service import get_fine_tuning_service
from app.services.task_queue import get_task_queue
from app.utils.monitoring import log_fine_tuning_job

logger = logging.getLogger(__name__)

class FineTuningScheduler:
    """Scheduler for fine-tuning jobs."""
    
    def __init__(self, interval_hours: int = 24):
        """
        Initialize the fine-tuning scheduler.
        
        Args:
            interval_hours: Interval in hours to check for new fine-tuning jobs
        """
        self.interval_hours = interval_hours
        self.running = False
        self.task = None
        self.fine_tuning_service = get_fine_tuning_service()
        self.task_queue = get_task_queue()
    
    async def start(self):
        """Start the scheduler."""
        if self.running:
            return
        
        self.running = True
        self.task = asyncio.create_task(self._schedule_loop())
        logger.info(f"Fine-tuning scheduler started with interval of {self.interval_hours} hours")
    
    async def stop(self):
        """Stop the scheduler."""
        if not self.running:
            return
        
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
            self.task = None
        
        logger.info("Fine-tuning scheduler stopped")
    
    async def _schedule_loop(self):
        """Main scheduling loop."""
        try:
            # Add some randomization to the start time to avoid all instances
            # starting at exactly the same time
            await asyncio.sleep(random.uniform(5, 60))
            
            while self.running:
                try:
                    await self._check_for_fine_tuning()
                except Exception as e:
                    logger.error(f"Error checking for fine-tuning: {str(e)}")
                
                # Sleep for the specified interval
                await asyncio.sleep(self.interval_hours * 3600)
        except asyncio.CancelledError:
            # Handle cancellation
            logger.info("Fine-tuning scheduler loop cancelled")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in fine-tuning scheduler: {str(e)}")
            self.running = False
            raise
    
    async def _check_for_fine_tuning(self):
        """Check if fine-tuning should be performed."""
        logger.info("Checking for fine-tuning candidates")
        
        # Check for pending jobs
        pending_jobs = await get_fine_tuning_jobs(status="pending")
        if pending_jobs:
            logger.info(f"Found {len(pending_jobs)} pending fine-tuning jobs. Will not create new ones.")
            return
        
        # Get candidates that haven't been processed
        start_date = datetime.utcnow() - timedelta(days=30)
        candidates = await get_fine_tuning_candidates(
            start_date=start_date,
            is_processed=False
        )
        
        # Check if we have enough candidates
        if len(candidates) < settings.fine_tuning_min_examples:
            logger.info(f"Not enough candidates for fine-tuning. Found {len(candidates)}, need {settings.fine_tuning_min_examples}")
            return
        
        logger.info(f"Found {len(candidates)} candidates for fine-tuning")
        
        # Group candidates by model and prepare fine-tuning data
        candidates_by_model = self._group_candidates_by_model(candidates)
        
        for model_name, model_candidates in candidates_by_model.items():
            if len(model_candidates) >= settings.fine_tuning_min_examples:
                await self._schedule_fine_tuning_job(model_name, model_candidates)
            else:
                logger.info(f"Not enough candidates for model {model_name}. Found {len(model_candidates)}, need {settings.fine_tuning_min_examples}")
    
    def _group_candidates_by_model(self, candidates: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group candidates by model.
        
        Args:
            candidates: List of fine-tuning candidates
            
        Returns:
            Dictionary mapping model names to lists of candidates
        """
        # Default model to use if not specified
        default_model = settings.default_model
        
        # Group by model
        result = {}
        
        for candidate in candidates:
            # Use the model from candidate if specified, otherwise use default
            model = candidate.get("model", default_model)
            
            if model not in result:
                result[model] = []
            
            result[model].append(candidate)
        
        return result
    
    async def _schedule_fine_tuning_job(self, model_name: str, candidates: List[Dict[str, Any]]):
        """
        Schedule a fine-tuning job.
        
        Args:
            model_name: The name of the model to fine-tune
            candidates: List of candidates for fine-tuning
        """
        # Create job ID
        job_id = str(uuid.uuid4())
        
        # Job name
        job_name = f"auto-ft-{model_name}-{datetime.utcnow().strftime('%Y%m%d')}"
        
        # Prepare job metadata
        job_metadata = {
            "id": job_id,
            "name": job_name,
            "status": "preparing",
            "created_at": datetime.utcnow().isoformat(),
            "scheduled_by": "auto-scheduler",
            "model_name": model_name,
            "examples_count": len(candidates),
            "hyperparameters": {
                "epochs": 3,
                "learning_rate": 5e-5,
                "batch_size": 4
            }
        }
        
        # Save job to database
        await save_fine_tuning_job(job_metadata)
        
        # Log the creation of the job
        log_fine_tuning_job("created")
        
        # Extract candidate IDs
        candidate_ids = [candidate["id"] for candidate in candidates if "id" in candidate]
        
        # Mark candidates as processed
        await mark_candidates_as_processed(candidate_ids)
        
        # Prepare training data
        training_data = await self._prepare_training_data(candidates)
        
        # Save training data to file
        training_file_path = self._save_training_data(job_id, training_data)
        
        # Update job with file path
        await self.fine_tuning_service.update_fine_tuning_job(job_id, {"training_file": training_file_path})
        
        # Queue the fine-tuning task
        await self.task_queue.add_task(
            task_name="fine_tuning",
            task_data={
                "job_id": job_id,
                "training_file": training_file_path,
                "model_name": model_name,
                "hyperparameters": job_metadata["hyperparameters"]
            },
            priority=5  # Lower priority than user-facing tasks
        )
        
        logger.info(f"Scheduled fine-tuning job {job_id} with {len(candidates)} examples for model {model_name}")
    
    async def _prepare_training_data(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Prepare training data from candidates.
        
        Args:
            candidates: List of fine-tuning candidates
            
        Returns:
            List of training examples
        """
        return await self.fine_tuning_service.prepare_fine_tuning_data(candidates)
    
    def _save_training_data(self, job_id: str, training_data: List[Dict[str, Any]]) -> str:
        """
        Save training data to a file.
        
        Args:
            job_id: The job ID
            training_data: The training data
            
        Returns:
            Path to the saved file
        """
        return self.fine_tuning_service._save_training_data(job_id, training_data)


# Singleton instance
_scheduler = None

def get_fine_tuning_scheduler() -> FineTuningScheduler:
    """Get the fine-tuning scheduler singleton instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = FineTuningScheduler()
    return _scheduler