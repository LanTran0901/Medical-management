from pydantic import BaseModel, Field


class RagChatRequest(BaseModel):
    question: str = Field(min_length=1, description="User question")
    session_id: str = Field(min_length=1, description="Conversation session id")


class RagChatSource(BaseModel):
    id: str
    entry_type: str
    title: str
    score: float
    summary: str | None = None


class RagChatResponse(BaseModel):
    answer: str
    session_id: str
    used_context_count: int
    sources: list[RagChatSource] = Field(default_factory=list)
