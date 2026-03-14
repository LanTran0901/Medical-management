from fastapi import APIRouter, HTTPException

from app.schemas.rag import RagChatRequest, RagChatResponse
from app.services.rag_graph import run_rag

router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/chat", response_model=RagChatResponse)
async def rag_chat(payload: RagChatRequest) -> RagChatResponse:
    try:
        result = await run_rag(question=payload.question, session_id=payload.session_id)
        return RagChatResponse(**result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"RAG flow failed: {exc}") from exc
