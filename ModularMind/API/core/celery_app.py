"""
Celery configuration and task queues
"""
from typing import Any, Dict, Optional
import os
from celery import Celery, Task
from celery.schedules import crontab
from pydantic import BaseSettings
import logging

# Configure logging
logger = logging.getLogger(__name__)

class CeleryConfig:
    """Celery configuration settings"""
    
    # Broker settings
    broker_url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
    
    # Backend settings
    result_backend = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
    
    # Task settings
    task_serializer = "json"
    accept_content = ["json"]
    result_serializer = "json"
    timezone = "UTC"
    enable_utc = True
    
    # Task execution settings
    worker_prefetch_multiplier = 1
    task_acks_late = True
    task_reject_on_worker_lost = True
    task_time_limit = 3600  # 1 hour
    task_soft_time_limit = 3000  # 50 minutes
    
    # Result settings
    result_expires = 3600 * 24 * 7  # 1 week
    
    # Beat settings
    beat_schedule = {
        'cleanup-every-hour': {
            'task': 'ModularMind.API.tasks.maintenance.cleanup_old_tasks',
            'schedule': crontab(minute=0),  # Run every hour
        },
        'update-embeddings-daily': {
            'task': 'ModularMind.API.tasks.embeddings.update_embeddings',
            'schedule': crontab(hour=2, minute=0),  # Run at 2 AM every day
            'args': (),
        },
    }
    
    # Task queues
    task_routes = {
        'ModularMind.API.tasks.embedding.*': {'queue': 'embedding'},
        'ModularMind.API.tasks.retrieval.*': {'queue': 'retrieval'},
        'ModularMind.API.tasks.multimodal.*': {'queue': 'multimodal'},
        'ModularMind.API.tasks.maintenance.*': {'queue': 'maintenance'},
        'ModularMind.API.tasks.scheduled.*': {'queue': 'scheduled'},
    }


# Create Celery app
celery_app = Celery("modularmind")
celery_app.config_from_object(CeleryConfig)


class LoggingTask(Task):
    """Base Celery task with logging"""
    
    def on_success(self, retval, task_id, args, kwargs):
        """Log successful task execution"""
        logger.info(
            f"Task {self.name}[{task_id}] succeeded: {retval}"
        )
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Log failed task execution"""
        logger.error(
            f"Task {self.name}[{task_id}] failed: {exc}\n{einfo}"
        )
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Log task retry"""
        logger.warning(
            f"Task {self.name}[{task_id}] retrying: {exc}"
        )


# Create task modules for cleaner imports
@celery_app.task(base=LoggingTask, bind=True, max_retries=3)
def example_task(self, x: int, y: int) -> int:
    """Example task that adds two numbers"""
    logger.info(f"Adding {x} + {y}")
    return x + y


# Helper function to get celery app
def get_celery_app() -> Celery:
    """
    Get the Celery app instance
    
    Returns:
        Celery: Celery app
    """
    return celery_app


def register_tasks():
    """Register all Celery tasks"""
    # Import tasks here to register them with Celery
    # This is to avoid circular imports
    from ModularMind.API.tasks import embedding, retrieval, multimodal, maintenance, scheduled
    
    logger.info("Celery tasks registered")