from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    users,
    documents,
    chat,
    query,
    retrieval,
    embeddings,
    models,
    tasks,
    multimodal,
    languages,
    feedback,
    fine_tuning_admin  # Yeni eklenen Fine-Tuning Admin modülü
)

api_router = APIRouter()

# Include all API routes
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(documents.router, prefix="/documents", tags=["Documents"])
api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])
api_router.include_router(query.router, prefix="/query", tags=["Query"])
api_router.include_router(retrieval.router, prefix="/retrieval", tags=["Retrieval"])
api_router.include_router(embeddings.router, prefix="/embeddings", tags=["Embeddings"])
api_router.include_router(models.router, prefix="/models", tags=["Models"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["Tasks"])
api_router.include_router(multimodal.router, prefix="/multimodal", tags=["Multimodal"])
api_router.include_router(languages.router, prefix="/languages", tags=["Languages"])
api_router.include_router(feedback.router, prefix="/feedback", tags=["Feedback"])
api_router.include_router(fine_tuning_admin.router, prefix="/admin/fine-tuning", tags=["Fine-Tuning"])