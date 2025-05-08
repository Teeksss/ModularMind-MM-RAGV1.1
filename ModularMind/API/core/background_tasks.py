"""
Background task management utilities
"""
from typing import Any, Callable, Dict, List, Optional, Union
import asyncio
import logging
import time
import traceback
import uuid
from datetime import datetime, timedelta
from enum import Enum
from pydantic import BaseModel
from fastapi import BackgroundTasks
from contextvars import ContextVar

# Configure logging
logger = logging.getLogger(__name__)

# Context variable to store current task ID
current_task_id: ContextVar[str] = ContextVar('current_task_id', default='')

class TaskStatus(str, Enum):
    """Task status enum"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class TaskInfo(BaseModel):
    """Task information model"""
    task_id: str
    status: TaskStatus
    name: str
    args: Dict[str, Any]
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: float = 0.0
    result: Optional[Any] = None
    error: Optional[str] = None
    retries: int = 0
    max_retries: int = 0


class BackgroundTaskManager:
    """Background task manager for handling long-running tasks"""
    
    def __init__(self, max_workers: int = 10):
        """Initialize the task manager"""
        self.max_workers = max_workers
        self.tasks: Dict[str, TaskInfo] = {}
        self.semaphore = asyncio.Semaphore(max_workers)
        self.task_queue = asyncio.Queue()
        self.executor_task = None
    
    async def start(self):
        """Start the task executor"""
        self.executor_task = asyncio.create_task(self._task_executor())
        logger.info(f"Background task manager started with {self.max_workers} workers")
    
    async def stop(self):
        """Stop the task executor"""
        if self.executor_task:
            self.executor_task.cancel()
            try:
                await self.executor_task
            except asyncio.CancelledError:
                logger.info("Task executor canceled")
        logger.info("Background task manager stopped")
    
    async def _task_executor(self):
        """Task executor that processes the task queue"""
        try:
            while True:
                # Get next task from queue
                task_id, func, args, kwargs = await self.task_queue.get()
                
                # Process the task
                asyncio.create_task(self._process_task(task_id, func, args, kwargs))
                
                # Mark the task as done in the queue
                self.task_queue.task_done()
        except asyncio.CancelledError:
            logger.info("Task executor loop canceled")
            raise
        except Exception as e:
            logger.error(f"Error in task executor: {e}\n{traceback.format_exc()}")
            # Restart the executor
            asyncio.create_task(self._task_executor())
    
    async def _process_task(self, task_id: str, func: Callable, args: list, kwargs: dict):
        """Process a single task"""
        # Acquire semaphore to limit concurrent tasks
        async with self.semaphore:
            # Update task status
            if task_id in self.tasks:
                self.tasks[task_id].status = TaskStatus.RUNNING
                self.tasks[task_id].started_at = datetime.utcnow()
            
            # Set context var for the current task
            token = current_task_id.set(task_id)
            
            try:
                # Execute the task
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    # Run in a thread pool for blocking functions
                    loop = asyncio.get_running_loop()
                    result = await loop.run_in_executor(
                        None, 
                        lambda: func(*args, **kwargs)
                    )
                
                # Update task with success result
                if task_id in self.tasks:
                    self.tasks[task_id].status = TaskStatus.COMPLETED
                    self.tasks[task_id].completed_at = datetime.utcnow()
                    self.tasks[task_id].result = result
                    self.tasks[task_id].progress = 1.0
                
                logger.info(f"Task {task_id} completed successfully")
                return result
                
            except Exception as e:
                # Update task with error
                if task_id in self.tasks:
                    task_info = self.tasks[task_id]
                    
                    # Check if we should retry
                    if task_info.retries < task_info.max_retries:
                        task_info.retries += 1
                        task_info.status = TaskStatus.PENDING
                        task_info.error = f"{type(e).__name__}: {str(e)}"
                        
                        # Add to queue again
                        logger.info(f"Retrying task {task_id} ({task_info.retries}/{task_info.max_retries})")
                        await self.task_queue.put((task_id, func, args, kwargs))
                    else:
                        # Max retries reached
                        task_info.status = TaskStatus.FAILED
                        task_info.completed_at = datetime.utcnow()
                        task_info.error = f"{type(e).__name__}: {str(e)}"
                        
                        logger.error(f"Task {task_id} failed: {e}\n{traceback.format_exc()}")
                
                # Re-raise the exception
                logger.error(f"Error in task {task_id}: {e}\n{traceback.format_exc()}")
                raise
            finally:
                # Reset context var
                current_task_id.reset(token)
    
    async def add_task(
        self,
        func: Callable,
        args: Optional[list] = None,
        kwargs: Optional[dict] = None,
        task_name: Optional[str] = None,
        max_retries: int = 0
    ) -> str:
        """
        Add a task to the queue
        
        Args:
            func: The function to execute
            args: Positional arguments for the function
            kwargs: Keyword arguments for the function
            task_name: Name of the task
            max_retries: Maximum number of retries
            
        Returns:
            str: Task ID
        """
        # Generate unique task ID
        task_id = str(uuid.uuid4())
        
        # Use function name if task name not provided
        if task_name is None:
            task_name = func.__name__
        
        # Default args and kwargs
        args = args or []
        kwargs = kwargs or {}
        
        # Extract named args from kwargs for storage
        named_args = {
            k: str(v) if not isinstance(v, (str, int, float, bool, type(None))) else v
            for k, v in kwargs.items()
        }
        
        # Create task info
        task_info = TaskInfo(
            task_id=task_id,
            status=TaskStatus.PENDING,
            name=task_name,
            args=named_args,
            created_at=datetime.utcnow(),
            max_retries=max_retries
        )
        
        # Store task info
        self.tasks[task_id] = task_info
        
        # Add task to queue
        await self.task_queue.put((task_id, func, args, kwargs))
        
        logger.info(f"Added task {task_id} ({task_name}) to queue")
        return task_id
    
    def get_task_info(self, task_id: str) -> Optional[TaskInfo]:
        """
        Get information about a task
        
        Args:
            task_id: Task ID
            
        Returns:
            Optional[TaskInfo]: Task information or None if not found
        """
        return self.tasks.get(task_id)
    
    def list_tasks(
        self,
        status: Optional[Union[TaskStatus, List[TaskStatus]]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[TaskInfo]:
        """
        List tasks with filtering
        
        Args:
            status: Filter by status
            limit: Maximum number of tasks to return
            offset: Offset for pagination
            
        Returns:
            List[TaskInfo]: List of task information
        """
        tasks = list(self.tasks.values())
        
        # Filter by status if specified
        if status:
            if isinstance(status, list):
                tasks = [t for t in tasks if t.status in status]
            else:
                tasks = [t for t in tasks if t.status == status]
        
        # Sort by created_at (newest first)
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        
        # Apply pagination
        return tasks[offset:offset + limit]
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a pending task
        
        Args:
            task_id: Task ID
            
        Returns:
            bool: True if task was canceled, False otherwise
        """
        if task_id in self.tasks:
            task_info = self.tasks[task_id]
            
            # Only pending tasks can be canceled
            if task_info.status == TaskStatus.PENDING:
                task_info.status = TaskStatus.CANCELED
                task_info.completed_at = datetime.utcnow()
                logger.info(f"Task {task_id} canceled")
                return True
        
        return False
    
    async def clean_old_tasks(self, max_age_hours: int = 24) -> int:
        """
        Clean up old completed/failed/canceled tasks
        
        Args:
            max_age_hours: Maximum age in hours
            
        Returns:
            int: Number of tasks removed
        """
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        to_remove = []
        
        for task_id, task in self.tasks.items():
            # Only clean completed, failed, or canceled tasks
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELED]:
                # Check if task is old enough
                if task.completed_at and task.completed_at < cutoff:
                    to_remove.append(task_id)
        
        # Remove tasks
        for task_id in to_remove:
            del self.tasks[task_id]
        
        logger.info(f"Cleaned up {len(to_remove)} old tasks")
        return len(to_remove)
    
    def update_task_progress(
        self,
        progress: float,
        message: Optional[str] = None
    ) -> None:
        """
        Update the progress of the current task
        
        Args:
            progress: Progress value (0.0 to 1.0)
            message: Optional status message
        """
        # Get current task ID from context
        task_id = current_task_id.get()
        if not task_id:
            logger.warning("Cannot update task progress: No current task ID in context")
            return
        
        # Update task info
        if task_id in self.tasks:
            self.tasks[task_id].progress = max(0.0, min(1.0, progress))
            
            # Optionally update result with message
            if message:
                self.tasks[task_id].result = message


# Global background task manager instance
task_manager = BackgroundTaskManager()


async def setup_background_tasks(app=None):
    """
    Set up the background task manager
    
    Args:
        app: Optional FastAPI app for lifecycle events
    """
    # Start the task manager
    await task_manager.start()
    
    # Set up clean up task
    async def clean_old_tasks():
        """Clean up old tasks periodically"""
        while True:
            try:
                await task_manager.clean_old_tasks()
            except Exception as e:
                logger.error(f"Error cleaning old tasks: {e}")
            
            # Wait for 1 hour
            await asyncio.sleep(3600)
    
    # Start cleanup task
    asyncio.create_task(clean_old_tasks())
    
    # Register shutdown handler if app is provided
    if app:
        @app.on_event("shutdown")
        async def on_shutdown():
            """Shutdown handler for the task manager"""
            await task_manager.stop()
    
    return task_manager


def get_task_manager() -> BackgroundTaskManager:
    """
    Get the global task manager instance
    
    Returns:
        BackgroundTaskManager: Global task manager
    """
    return task_manager


def update_progress(progress: float, message: Optional[str] = None) -> None:
    """
    Update the progress of the current task
    
    Args:
        progress: Progress value (0.0 to 1.0)
        message: Optional status message
    """
    task_manager.update_task_progress(progress, message)