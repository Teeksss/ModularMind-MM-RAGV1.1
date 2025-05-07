import logging
import os
import json
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid

from app.core.config import settings
from app.db.crud.fine_tuning import save_fine_tuning_job, update_fine_tuning_job, get_fine_tuning_job
from app.services.llm_service import get_llm_service
from app.services.task_queue import get_task_queue

logger = logging.getLogger(__name__)

class FineTuningService:
    """Service for fine-tuning language models based on user feedback."""
    
    def __init__(self):
        self.llm_service = get_llm_service()
        self.task_queue = get_task_queue()
        self.fine_tuning_dir = os.path.join(settings.storage_path, "fine_tuning")
        
        # Create directory if it doesn't exist
        os.makedirs(self.fine_tuning_dir, exist_ok=True)
    
    async def start_fine_tuning_job(self, training_data: List[Dict[str, Any]], job_name: Optional[str] = None) -> str:
        """
        Start a fine-tuning job.
        
        Args:
            training_data: List of training examples
            job_name: Optional name for the job
            
        Returns:
            str: Job ID
        """
        # Generate job ID and name
        job_id = str(uuid.uuid4())
        job_name = job_name or f"fine-tuning-{job_id[:8]}"
        
        # Prepare job metadata
        job_metadata = {
            "id": job_id,
            "name": job_name,
            "status": "preparing",
            "created_at": datetime.utcnow().isoformat(),
            "examples_count": len(training_data),
            "model_name": settings.default_model,
            "hyperparameters": {
                "epochs": 3,
                "learning_rate": 5e-5,
                "batch_size": 4
            }
        }
        
        # Save job to database
        await save_fine_tuning_job(job_metadata)
        
        # Save training data to file
        training_file_path = self._save_training_data(job_id, training_data)
        
        # Update job with file path
        job_metadata["training_file"] = training_file_path
        await update_fine_tuning_job(job_id, {"training_file": training_file_path})
        
        # Queue the fine-tuning task
        await self.task_queue.add_task(
            task_name="fine_tuning",
            task_data={
                "job_id": job_id,
                "training_file": training_file_path,
                "model_name": job_metadata["model_name"],
                "hyperparameters": job_metadata["hyperparameters"]
            },
            priority=5  # Lower priority than user-facing tasks
        )
        
        logger.info(f"Queued fine-tuning job {job_id} with {len(training_data)} examples")
        
        return job_id
    
    async def execute_fine_tuning(self, job_id: str) -> bool:
        """
        Execute a fine-tuning job.
        
        Args:
            job_id: The ID of the fine-tuning job
            
        Returns:
            bool: Whether the job was successful
        """
        try:
            # Get job data
            job_data = await get_fine_tuning_job(job_id)
            if not job_data:
                logger.error(f"Fine-tuning job {job_id} not found")
                return False
            
            # Update job status
            await update_fine_tuning_job(job_id, {"status": "running"})
            
            # Load training data
            training_file = job_data.get("training_file")
            if not training_file or not os.path.exists(training_file):
                logger.error(f"Training file not found for job {job_id}")
                await update_fine_tuning_job(job_id, {"status": "failed", "error": "Training file not found"})
                return False
            
            # For OpenAI models
            if settings.llm_service_type == "openai":
                return await self._fine_tune_openai(job_id, job_data)
            
            # For local models
            elif settings.llm_service_type == "local":
                return await self._fine_tune_local(job_id, job_data)
                
            else:
                logger.error(f"Unsupported LLM service type: {settings.llm_service_type}")
                await update_fine_tuning_job(job_id, {
                    "status": "failed", 
                    "error": f"Unsupported LLM service type: {settings.llm_service_type}"
                })
                return False
                
        except Exception as e:
            logger.error(f"Error executing fine-tuning job {job_id}: {str(e)}")
            await update_fine_tuning_job(job_id, {"status": "failed", "error": str(e)})
            return False
    
    async def _fine_tune_openai(self, job_id: str, job_data: Dict[str, Any]) -> bool:
        """
        Fine-tune using OpenAI API.
        
        Args:
            job_id: The job ID
            job_data: The job data
            
        Returns:
            bool: Whether the job was successful
        """
        try:
            # Convert training data to OpenAI format
            openai_format_path = self._convert_to_openai_format(job_data["training_file"])
            
            # Upload file to OpenAI
            file_response = await self.llm_service.api.files.create(
                file=open(openai_format_path, "rb"),
                purpose="fine-tune"
            )
            
            file_id = file_response.id
            
            # Create fine-tuning job
            response = await self.llm_service.api.fine_tuning.jobs.create(
                training_file=file_id,
                model=job_data["model_name"],
                hyperparameters=job_data["hyperparameters"]
            )
            
            # Update job with API job ID
            await update_fine_tuning_job(job_id, {
                "provider_job_id": response.id,
                "status": "submitted"
            })
            
            # Start monitoring job status
            asyncio.create_task(self._monitor_openai_job(job_id, response.id))
            
            return True
            
        except Exception as e:
            logger.error(f"Error starting OpenAI fine-tuning: {str(e)}")
            await update_fine_tuning_job(job_id, {"status": "failed", "error": str(e)})
            return False
    
    async def _fine_tune_local(self, job_id: str, job_data: Dict[str, Any]) -> bool:
        """
        Fine-tune a local model.
        
        Args:
            job_id: The job ID
            job_data: The job data
            
        Returns:
            bool: Whether the job was successful
        """
        # This is a placeholder for local model fine-tuning
        # In practice, you would implement model-specific fine-tuning logic
        
        try:
            # Update status
            await update_fine_tuning_job(job_id, {"status": "processing"})
            
            # Simulate fine-tuning process
            await asyncio.sleep(10)
            
            # Update with success
            await update_fine_tuning_job(job_id, {
                "status": "completed",
                "completed_at": datetime.utcnow().isoformat(),
                "fine_tuned_model": f"ft-{job_data['model_name']}-{job_id[:8]}"
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Error in local fine-tuning: {str(e)}")
            await update_fine_tuning_job(job_id, {"status": "failed", "error": str(e)})
            return False
    
    async def _monitor_openai_job(self, job_id: str, openai_job_id: str):
        """
        Monitor an OpenAI fine-tuning job.
        
        Args:
            job_id: Our internal job ID
            openai_job_id: The OpenAI job ID
        """
        try:
            # Loop until job is done
            while True:
                # Get job status
                response = await self.llm_service.api.fine_tuning.jobs.retrieve(openai_job_id)
                
                # Update job status
                status_mapping = {
                    "validating_files": "validating",
                    "queued": "queued",
                    "running": "running",
                    "succeeded": "completed",
                    "failed": "failed",
                    "cancelled": "cancelled"
                }
                
                mapped_status = status_mapping.get(response.status, response.status)
                
                update_data = {"status": mapped_status}
                
                # Add additional data if job is complete
                if response.status == "succeeded":
                    update_data["completed_at"] = datetime.utcnow().isoformat()
                    update_data["fine_tuned_model"] = response.fine_tuned_model
                elif response.status == "failed":
                    update_data["error"] = response.error.message if response.error else "Unknown error"
                
                await update_fine_tuning_job(job_id, update_data)
                
                # Exit if job is done
                if response.status in ["succeeded", "failed", "cancelled"]:
                    break
                
                # Wait before checking again
                await asyncio.sleep(60)  # Check every minute
                
        except Exception as e:
            logger.error(f"Error monitoring OpenAI job {openai_job_id}: {str(e)}")
            await update_fine_tuning_job(job_id, {"status": "monitoring_failed", "error": str(e)})
    
    def _save_training_data(self, job_id: str, training_data: List[Dict[str, Any]]) -> str:
        """
        Save training data to a file.
        
        Args:
            job_id: The job ID
            training_data: The training data
            
        Returns:
            str: Path to the saved file
        """
        file_path = os.path.join(self.fine_tuning_dir, f"{job_id}_training_data.json")
        
        with open(file_path, "w") as f:
            json.dump(training_data, f, indent=2)
            
        return file_path
    
    def _convert_to_openai_format(self, input_file: str) -> str:
        """
        Convert training data to OpenAI JSONL format.
        
        Args:
            input_file: Path to input file
            
        Returns:
            str: Path to converted file
        """
        output_file = input_file.replace(".json", "_openai.jsonl")
        
        # Load input data
        with open(input_file, "r") as f:
            data = json.load(f)
        
        # Convert to OpenAI format
        with open(output_file, "w") as f:
            for example in data:
                openai_example = {
                    "messages": [
                        {"role": "user", "content": example["query"]},
                        {"role": "assistant", "content": example["response"]}
                    ]
                }
                f.write(json.dumps(openai_example) + "\n")
                
        return output_file

# Create a singleton instance
_fine_tuning_service = None

def get_fine_tuning_service() -> FineTuningService:
    """Get the fine-tuning service singleton instance."""
    global _fine_tuning_service
    if _fine_tuning_service is None:
        _fine_tuning_service = FineTuningService()
    return _fine_tuning_service