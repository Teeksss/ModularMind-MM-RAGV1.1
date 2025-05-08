from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from app.models.agent import Agent, AgentCreate, AgentUpdate
from app.services.agent_service import AgentService
from app.core.auth import get_current_user
from app.schemas.agent import AgentResponse, AgentList
from app.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

@router.post("/agents", response_model=AgentResponse)
async def create_agent(
    agent_data: AgentCreate,
    current_user = Depends(get_current_user),
    agent_service: AgentService = Depends()
):
    try:
        agent = await agent_service.create_agent(agent_data, current_user.id)
        return AgentResponse(
            status="success",
            data=agent,
            message="Agent created successfully"
        )
    except Exception as e:
        logger.error(f"Error creating agent: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/agents", response_model=AgentList)
async def get_agents(
    current_user = Depends(get_current_user),
    agent_service: AgentService = Depends(),
    skip: int = 0,
    limit: int = 10,
    status: Optional[str] = None
):
    try:
        agents = await agent_service.get_agents(
            user_id=current_user.id,
            skip=skip,
            limit=limit,
            status=status
        )
        return AgentList(
            status="success",
            data=agents,
            total=len(agents),
            skip=skip,
            limit=limit
        )
    except Exception as e:
        logger.error(f"Error fetching agents: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/agents/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    current_user = Depends(get_current_user),
    agent_service: AgentService = Depends()
):
    try:
        agent = await agent_service.get_agent(agent_id, current_user.id)
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent with ID {agent_id} not found"
            )
        return AgentResponse(
            status="success",
            data=agent
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching agent {agent_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.put("/agents/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str,
    agent_update: AgentUpdate,
    current_user = Depends(get_current_user),
    agent_service: AgentService = Depends()
):
    try:
        updated_agent = await agent_service.update_agent(
            agent_id,
            agent_update,
            current_user.id
        )
        return AgentResponse(
            status="success",
            data=updated_agent,
            message="Agent updated successfully"
        )
    except Exception as e:
        logger.error(f"Error updating agent {agent_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.delete("/agents/{agent_id}", response_model=AgentResponse)
async def delete_agent(
    agent_id: str,
    current_user = Depends(get_current_user),
    agent_service: AgentService = Depends()
):
    try:
        await agent_service.delete_agent(agent_id, current_user.id)
        return AgentResponse(
            status="success",
            message="Agent deleted successfully"
        )
    except Exception as e:
        logger.error(f"Error deleting agent {agent_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/agents/{agent_id}/execute", response_model=AgentResponse)
async def execute_task(
    agent_id: str,
    task: Dict[str, Any],
    current_user = Depends(get_current_user),
    agent_service: AgentService = Depends()
):
    try:
        result = await agent_service.execute_task(agent_id, task, current_user.id)
        return AgentResponse(
            status="success",
            data=result,
            message="Task executed successfully"
        )
    except Exception as e:
        logger.error(f"Error executing task for agent {agent_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )