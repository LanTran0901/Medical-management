from pydantic import BaseModel, Field


class RagChatRequest(BaseModel):
    question: str = Field(min_length=1, description="User question")
    session_id: str = Field(min_length=1, description="Conversation session id")


class RagChatResponse(BaseModel):
    answer: str
    session_id: str
    used_context_count: int
