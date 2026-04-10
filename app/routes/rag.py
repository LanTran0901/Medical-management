from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_current_user, get_rag_service
from app.application.usecases.rag_usecases import MedicalRagService
from app.domain.entities.user import User
from app.schemas.rag import RagChatRequest, RagChatResponse
from app.services.rag_graph import run_rag

router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/chat", response_model=RagChatResponse)
async def rag_chat(
    payload: RagChatRequest,
    rag_service: MedicalRagService = Depends(get_rag_service),
    current_user: User = Depends(get_current_user),
) -> RagChatResponse:
    try:
        result = await run_rag(
            question=payload.question,
            user_id=str(current_user.id),
            rag_service=rag_service,
        )
        return RagChatResponse(**result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"RAG flow failed: {exc}") from exc
