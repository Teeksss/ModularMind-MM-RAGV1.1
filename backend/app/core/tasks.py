import asyncio
import logging
from typing import Dict, Any, Callable, Awaitable, Optional, List, Union
import uuid
import time
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime

logger = logging.getLogger(__name__)

# Task status enum
class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Task model
class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: float = 0.0  # 0.0 to 1.0
    result: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


# Task Queue Manager
class TaskQueue:
    def __init__(self, max_workers: int = 5):
        self.max_workers = max_workers
        self.queue: asyncio.Queue = asyncio.Queue()
        self.tasks: Dict[str, Task] = {}
        self.workers: List[asyncio.Task] = []
        self.running = False
        
    async def start(self):
        """Start the worker tasks."""
        if self.running:
            return
        
        self.running = True
        
        # Start worker tasks
        for _ in range(self.max_workers):
            worker = asyncio.create_task(self._worker())
            self.workers.append(worker)
            
        logger.info(f"Task queue started with {self.max_workers} workers")
        
    async def stop(self):
        """Stop the worker tasks."""
        if not self.running:
            return
        
        self.running = False
        
        # Wait for all workers to finish
        await self.queue.join()
        
        # Cancel any pending tasks
        for worker in self.workers:
            worker.cancel()
            
        # Wait for all workers to be cancelled
        await asyncio.gather(*self.workers, return_exceptions=True)
        
        self.workers = []
        
        logger.info("Task queue stopped")
        
    async def enqueue(
        self,
        task_func: Callable[[Dict[str, Any]], Awaitable[Any]],
        name: str,
        metadata: Dict[str, Any] = None,
        **kwargs
    ) -> Task:
        """
        Add a task to the queue.
        
        Args:
            task_func: Async function to execute
            name: Name of the task
            metadata: Additional metadata
            **kwargs: Arguments to pass to the task function
            
        Returns:
            Task: Task object with ID for tracking
        """
        # Create task
        task = Task(
            name=name,
            metadata=metadata or {},
        )
        
        # Add to tracking dict
        self.tasks[task.id] = task
        
        # Add to queue
        await self.queue.put((task, task_func, kwargs))
        
        logger.info(f"Task {task.id} ({name}) added to queue")
        
        return task
        
    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        return self.tasks.get(task_id)
        
    async def cancel_task(self, task_id: str) -> bool:
        """
        Try to cancel a task. Only works for pending tasks.
        
        Returns:
            bool: True if cancelled, False otherwise
        """
        if task_id not in self.tasks:
            return False
            
        task = self.tasks[task_id]
        
        if task.status != TaskStatus.PENDING:
            return False
            
        task.status = TaskStatus.CANCELLED
        
        logger.info(f"Task {task_id} cancelled")
        
        return True
        
    async def _worker(self):
        """Worker task that processes items from the queue."""
        while self.running:
            try:
                # Get a task from the queue
                task, task_func, kwargs = await self.queue.get()
                
                # Skip cancelled tasks
                if task.status == TaskStatus.CANCELLED:
                    self.queue.task_done()
                    continue
                
                # Update task status
                task.status = TaskStatus.RUNNING
                task.started_at = datetime.utcnow()
                
                try:
                    # Execute the task
                    logger.info(f"Executing task {task.id}")
                    result = await task_func(**kwargs, task=task)
                    
                    # Update task with result
                    task.result = result
                    task.status = TaskStatus.COMPLETED
                    task.completed_at = datetime.utcnow()
                    task.progress = 1.0
                    
                    logger.info(f"Task {task.id} completed")
                    
                except Exception as e:
                    # Handle task error
                    logger.error(f"Task {task.id} failed: {str(e)}", exc_info=True)
                    task.status = TaskStatus.FAILED
                    task.error = str(e)
                    task.completed_at = datetime.utcnow()
                
                finally:
                    # Mark task as done
                    self.queue.task_done()
                    
            except asyncio.CancelledError:
                # Worker is being cancelled
                break
                
            except Exception as e:
                # Unexpected error in worker
                logger.error(f"Worker error: {str(e)}", exc_info=True)


# Global task queue instance
_task_queue = None

def get_task_queue() -> TaskQueue:
    """Get the global task queue instance."""
    global _task_queue
    if _task_queue is None:
        _task_queue = TaskQueue()
    return _task_queue

# Example document processing task
async def process_document(
    document_id: str,
    user_id: Optional[str] = None,
    task: Optional[Task] = None
) -> Dict[str, Any]:
    """
    Process a document (example task).
    
    Args:
        document_id: ID of the document to process
        user_id: ID of the user who owns the document
        task: Task object for status updates
        
    Returns:
        Dict with processing results
    """
    from app.db.session import get_db
    from app.models.document import Document, DocumentChunk
    from app.services.document_processor import DocumentProcessor
    
    # Update progress
    if task:
        task.progress = 0.1
        task.metadata["document_id"] = document_id
        if user_id:
            task.metadata["user_id"] = user_id
    
    # Get document from database
    async with get_db() as db:
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise ValueError(f"Document {document_id} not found")
            
        # Update progress
        if task:
            task.progress = 0.2
            
        # Process document
        processor = DocumentProcessor()
        result = await processor.process(document, task)
        
        # Update document status
        document.is_processed = True
        db.commit()
        
    return result