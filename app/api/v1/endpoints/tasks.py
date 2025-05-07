from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.api.deps import get_current_user, get_current_admin_user
from app.models.user import User
from app.core.tasks import get_task_queue, TaskStatus

router = APIRouter()


@router.get(
    "/",
    summary="List all tasks"
)
async def list_tasks(
    status: Optional[TaskStatus] = None,
    limit: int = 10,
    offset: int = 0,
    current_user: User = Depends(get_current_admin_user)
):
    """List all tasks (admin only)."""
    task_queue = get_task_queue()
    
    # Get tasks from queue
    tasks = list(task_queue.tasks.values())
    
    # Filter by status if provided
    if status:
        tasks = [task for task in tasks if task.status == status]
    
    # Sort by creation time (newest first)
    tasks.sort(key=lambda t: t.created_at, reverse=True)
    
    # Apply pagination
    paginated_tasks = tasks[offset:offset+limit]
    
    return {
        "tasks": paginated_tasks,
        "total": len(tasks),
        "limit": limit,
        "offset": offset
    }


@router.get(
    "/{task_id}",
    summary="Get task details"
)
async def get_task(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get details of a specific task."""
    task_queue = get_task_queue()
    
    # Get task from queue
    task = await task_queue.get_task(task_id)
    
    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"Task not found: {task_id}"
        )
    
    # Check if user has permission to view this task
    is_admin = current_user.is_admin
    task_user_id = task.metadata.get("user_id")
    
    if not is_admin and task_user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to view this task"
        )
    
    return task


@router.post(
    "/{task_id}/cancel",
    summary="Cancel a task"
)
async def cancel_task(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """Cancel a pending task."""
    task_queue = get_task_queue()
    
    # Get task from queue
    task = await task_queue.get_task(task_id)
    
    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"Task not found: {task_id}"
        )
    
    # Check if user has permission to cancel this task
    is_admin = current_user.is_admin
    task_user_id = task.metadata.get("user_id")
    
    if not is_admin and task_user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to cancel this task"
        )
    
    # Can only cancel pending tasks
    if task.status != TaskStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel task with status {task.status}"
        )
    
    # Cancel the task
    cancelled = await task_queue.cancel_task(task_id)
    
    if cancelled:
        return {
            "message": f"Task {task_id} cancelled successfully",
            "status": TaskStatus.CANCELLED
        }
    else:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel task {task_id}"
        )


@router.get(
    "/user/{user_id}",
    summary="List user's tasks"
)
async def list_user_tasks(
    user_id: str,
    status: Optional[TaskStatus] = None,
    limit: int = 10,
    offset: int = 0,
    current_user: User = Depends(get_current_user)
):
    """List tasks for a specific user."""
    # Check permissions
    is_admin = current_user.is_admin
    is_self = current_user.id == user_id
    
    if not is_admin and not is_self:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to view tasks for this user"
        )
    
    task_queue = get_task_queue()
    
    # Get all tasks
    all_tasks = list(task_queue.tasks.values())
    
    # Filter tasks for the specific user
    user_tasks = [
        task for task in all_tasks 
        if task.metadata.get("user_id") == user_id
    ]
    
    # Filter by status if provided
    if status:
        user_tasks = [task for task in user_tasks if task.status == status]
    
    # Sort by creation time (newest first)
    user_tasks.sort(key=lambda t: t.created_at, reverse=True)
    
    # Apply pagination
    paginated_tasks = user_tasks[offset:offset+limit]
    
    return {
        "tasks": paginated_tasks,
        "total": len(user_tasks),
        "limit": limit,
        "offset": offset
    }