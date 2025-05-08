from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth,
    agents,
    rag,
    users,
    documents,
    metrics,
    chat,
    admin,
    webhooks
)

api_router = APIRouter()

# Auth routes
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["authentication"]
)

# Agent routes
api_router.include_router(
    agents.router,
    prefix="/agents",
    tags=["agents"]
)

# RAG routes
api_router.include_router(
    rag.router,
    prefix="/rag",
    tags=["rag"]
)

# User routes
api_router.include_router(
    users.router,
    prefix="/users",
    tags=["users"]
)

# Document routes
api_router.include_router(
    documents.router,
    prefix="/documents",
    tags=["documents"]
)

# Metrics routes
api_router.include_router(
    metrics.router,
    prefix="/metrics",
    tags=["metrics"]
)

# Chat routes
api_router.include_router(
    chat.router,
    prefix="/chat",
    tags=["chat"]
)

# Admin routes
api_router.include_router(
    admin.router,
    prefix="/admin",
    tags=["admin"]
)

# Webhook routes
api_router.include_router(
    webhooks.router,
    prefix="/webhooks",
    tags=["webhooks"]
)