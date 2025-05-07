import asyncio
import logging
import time
import uuid
import os
import signal
import json
from typing import Dict, List, Any, Optional, Callable, Union
from datetime import datetime, timedelta

from app.core.config import settings
from app.db.mongodb import get_database
from app.utils.monitoring import track_task_execution, update_task_queue_size

logger = logging.getLogger(__name__)

class TaskStatus:
    """Task status constants."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskQueueWorker:
    """Worker for processing tasks from the task queue."""
    
    def __init__(
        self,
        worker_id: str = None,
        poll_interval: float = 1.0,
        max_tasks: int = 10,
        task_handlers: Dict[str, Callable] = None
    ):
        """
        Initialize the task queue worker.
        
        Args:
            worker_id: Unique identifier for this worker
            poll_interval: Time in seconds to wait between polling for new tasks
            max_tasks: Maximum number of tasks to process at once
            task_handlers: Dictionary mapping task names to handler functions
        """
        self.worker_id = worker_id or f"worker-{uuid.uuid4()}"
        self.poll_interval = poll_interval
        self.max_tasks = max_tasks
        self.running = False
        self.task_handlers = task_handlers or {}
        self.active_tasks = {}
        self.db = None
    
    async def start(self):
        """Start the worker."""
        if self.running:
            return
        
        logger.info(f"Starting task queue worker {self.worker_id}")
        self.running = True
        self.db = await get_database()
        
        # Register signal handlers for graceful shutdown
        self._register_signal_handlers()
        
        # Start the worker loop
        asyncio.create_task(self._worker_loop())
    
    async def stop(self):
        """Stop the worker."""
        if not self.running:
            return
        
        logger.info(f"Stopping task queue worker {self.worker_id}")
        self.running = False
        
        # Wait for active tasks to complete
        await self._wait_for_active_tasks()
    
    def register_task_handler(self, task_name: str, handler: Callable):
        """
        Register a handler for a specific task type.
        
        Args:
            task_name: The name of the task
            handler: The handler function for the task
        """
        self.task_handlers[task_name] = handler
        logger.info(f"Registered handler for task type '{task_name}'")
    
    async def _worker_loop(self):
        """Main worker loop."""
        try:
            while self.running:
                # Try to claim a task
                task = await self._claim_next_task()
                
                if task:
                    # Process the task asynchronously
                    asyncio.create_task(self._process_task(task))
                else:
                    # Wait before polling again
                    await asyncio.sleep(self.poll_interval)
                
                # Update task queue sizes for monitoring
                await self._update_queue_metrics()
        except Exception as e:
            logger.error(f"Error in worker loop: {str(e)}")
            self.running = False
    
    async def _claim_next_task(self) -> Optional[Dict[str, Any]]:
        """
        Claim the next available task from the queue.
        
        Returns:
            The claimed task or None if no task is available
        """
        # Check if we're at max capacity
        if len(self.active_tasks) >= self.max_tasks:
            return None
        
        # Find and claim a task atomically
        now = datetime.utcnow()
        
        try:
            # Find a task that's not already claimed
            # Sort by priority (higher first) and then creation time
            result = await self.db.tasks.find_one_and_update(
                {
                    "status": TaskStatus.PENDING,
                    "$or": [
                        {"claimed_by": None},
                        {"claimed_at": {"$lt": now - timedelta(minutes=10)}}  # Handle stale claims
                    ]
                },
                {
                    "$set": {
                        "status": TaskStatus.RUNNING,
                        "claimed_by": self.worker_id,
                        "claimed_at": now,
                        "started_at": now
                    }
                },
                sort=[("priority", -1), ("created_at", 1)],
                return_document=True
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error claiming task: {str(e)}")
            return None
    
    async def _process_task(self, task: Dict[str, Any]):
        """
        Process a task.
        
        Args:
            task: The task to process
        """
        task_id = str(task["_id"])
        task_name = task.get("name", "unknown")
        task_data = task.get("data", {})
        
        logger.info(f"Processing task {task_id} of type '{task_name}'")
        
        # Keep track of active task
        self.active_tasks[task_id] = task
        
        try:
            # Check if we have a handler for this task type
            if task_name not in self.task_handlers:
                logger.error(f"No handler registered for task type '{task_name}'")
                await self._mark_task_failed(task_id, f"No handler for task type '{task_name}'")
                return
            
            # Execute the task with monitoring
            with track_task_execution(task_name):
                handler = self.task_handlers[task_name]
                result = await handler(task_data)
            
            # Mark task as completed
            await self._mark_task_completed(task_id, result)
            
        except Exception as e:
            logger.error(f"Error processing task {task_id}: {str(e)}")
            await self._mark_task_failed(task_id, str(e))
        finally:
            # Remove from active tasks
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]
    
    async def _mark_task_completed(self, task_id: str, result: Any):
        """
        Mark a task as completed.
        
        Args:
            task_id: The ID of the task
            result: The result of the task
        """
        now = datetime.utcnow()
        
        try:
            await self.db.tasks.update_one(
                {"_id": task_id},
                {
                    "$set": {
                        "status": TaskStatus.COMPLETED,
                        "completed_at": now,
                        "result": result,
                        "updated_at": now
                    }
                }
            )
            
            logger.info(f"Task {task_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Error marking task {task_id} as completed: {str(e)}")
    
    async def _mark_task_failed(self, task_id: str, error: str):
        """
        Mark a task as failed.
        
        Args:
            task_id: The ID of the task
            error: The error message
        """
        now = datetime.utcnow()
        
        try:
            await self.db.tasks.update_one(
                {"_id": task_id},
                {
                    "$set": {
                        "status": TaskStatus.FAILED,
                        "error": error,
                        "completed_at": now,
                        "updated_at": now
                    }
                }
            )
            
            logger.error(f"Task {task_id} failed: {error}")
            
        except Exception as e:
            logger.error(f"Error marking task {task_id} as failed: {str(e)}")
    
    async def _update_queue_metrics(self):
        """Update queue size metrics."""
        try:
            # Count tasks by status and priority
            pipeline = [
                {
                    "$group": {
                        "_id": {
                            "status": "$status",
                            "priority": "$priority"
                        },
                        "count": {"$sum": 1}
                    }
                }
            ]
            
            results = await self.db.tasks.aggregate(pipeline).to_list(length=100)
            
            # Update metrics
            for result in results:
                status = result["_id"]["status"]
                priority = result["_id"]["priority"]
                count = result["count"]
                
                # Convert priority to string (high, medium, low)
                priority_str = "high" if priority >= 8 else "medium" if priority >= 4 else "low"
                
                # Update monitoring metrics
                update_task_queue_size(f"tasks_{status}", priority_str, count)
                
        except Exception as e:
            logger.error(f"Error updating queue metrics: {str(e)}")
    
    async def _wait_for_active_tasks(self, timeout: float = 30.0):
        """
        Wait for active tasks to complete.
        
        Args:
            timeout: Maximum time to wait in seconds
        """
        if not self.active_tasks:
            return
        
        logger.info(f"Waiting for {len(self.active_tasks)} active tasks to complete")
        
        start_time = time.time()
        while self.active_tasks and (time.time() - start_time) < timeout:
            await asyncio.sleep(0.5)
        
        if self.active_tasks:
            logger.warning(f"{len(self.active_tasks)} tasks still active after timeout")
    
    def _register_signal_handlers(self):
        """Register signal handlers for graceful shutdown."""
        def handle_signal(sig, frame):
            logger.info(f"Received signal {sig}, shutting down...")
            asyncio.create_task(self.stop())
        
        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)


# Task handler example
async def fine_tuning_task_handler(task_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle fine-tuning tasks.
    
    Args:
        task_data: Task data containing fine-tuning parameters
        
    Returns:
        Result of the fine-tuning process
    """
    from app.services.fine_tuning_service import get_fine_tuning_service
    
    job_id = task_data.get("job_id")
    if not job_id:
        raise ValueError("Missing job_id in task data")
    
    fine_tuning_service = get_fine_tuning_service()
    success = await fine_tuning_service.execute_fine_tuning(job_id)
    
    return {
        "success": success,
        "job_id": job_id
    }


# Worker factory function
def create_task_queue_worker(worker_id: str = None) -> TaskQueueWorker:
    """
    Create a task queue worker with the default handlers.
    
    Args:
        worker_id: Optional worker ID
        
    Returns:
        A configured task queue worker
    """
    worker = TaskQueueWorker(worker_id=worker_id)
    
    # Register handlers for different task types
    worker.register_task_handler("fine_tuning", fine_tuning_task_handler)
    
    # Register other handlers as needed
    
    return worker


# Main entry point for running a worker as a standalone process
async def main():
    """Main function when running as a script."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    logger.info("Starting task queue worker")
    
    # Create and start the worker
    worker = create_task_queue_worker()
    await worker.start()
    
    # Keep the worker running
    try:
        while True:
            await asyncio.sleep(3600)  # Sleep for an hour
    except asyncio.CancelledError:
        # Handle cancellation
        logger.info("Worker cancelled, shutting down")
    finally:
        # Stop the worker
        await worker.stop()


if __name__ == "__main__":
    asyncio.run(main())