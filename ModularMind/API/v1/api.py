from fastapi import APIRouter

from ModularMind.API.v1.endpoints import (
    auth,
    chat,
    documents,
    embeddings,
    feedback,
    fine_tuning_admin,
    health_check,
    languages,
    models,
    multimodal,
    query,
    retrieval,
    tasks,
    users
)

api_router = APIRouter(prefix="/api/v1")

# Auth endpoints
api_router.include_router(auth.router)

# Documents endpoints
api_router.include_router(documents.router)

# Chat endpoints
api_router.include_router(chat.router)

# Query endpoints
api_router.include_router(query.router)

# Retrieval endpoints
api_router.include_router(retrieval.router)

# Users endpoints
api_router.include_router(users.router)

# Models endpoints
api_router.include_router(models.router)

# Embeddings endpoints
api_router.include_router(embeddings.router)

# Feedback endpoints
api_router.include_router(feedback.router)

# Languages endpoints
api_router.include_router(languages.router)

# Multimodal endpoints
api_router.include_router(multimodal.router)

# Fine-tuning admin endpoints
api_router.include_router(fine_tuning_admin.router)

# Tasks endpoints
api_router.include_router(tasks.router)

# Health check endpoints
api_router.include_router(health_check.router)