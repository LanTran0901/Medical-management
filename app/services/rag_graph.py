from __future__ import annotations

from typing import Any, TypedDict

from langchain_groq import ChatGroq
from langgraph.graph import END, START, StateGraph

from app.application.usecases.rag_usecases import MedicalRagService
from app.core.config import settings
from app.infrastructure.config.database.mongodb import connection as mongodb


class RagState(TypedDict):
    question: str
    session_id: str
    contexts: list[str]
    sources: list[dict[str, Any]]
    answer: str


def _build_rag_graph(rag_service: MedicalRagService):
    async def load_context_from_postgres(state: RagState) -> RagState:
        retrieved = await rag_service.retrieve_sources(question=state["question"])
        state["contexts"] = [item.context_text for item in retrieved]
        state["sources"] = [
            {
                "id": item.id,
                "entry_type": item.entry_type,
                "title": item.title,
                "score": item.score,
                "summary": item.summary,
            }
            for item in retrieved
        ]
        return state

    async def generate_answer(state: RagState) -> RagState:
        if not state["contexts"]:
            state["answer"] = (
                "Mình chưa tìm thấy thông tin phù hợp trong kho tri thức nội bộ "
                "từ 3 bảng disease, drug và vaccine để trả lời câu hỏi này."
            )
            return state

        llm = ChatGroq(
            api_key=settings.groq_api_key,
            model=settings.groq_model,
            temperature=0,
        )

        context_text = "\n\n---\n\n".join(state["contexts"])
        prompt = (
            "Bạn là chatbot hỏi đáp y tế cho hệ thống Medical Management.\n"
            "Chỉ được trả lời dựa trên DUY NHẤT phần ngữ cảnh nội bộ đã truy xuất bên dưới.\n"
            "Nếu dữ liệu không đủ để kết luận, hãy nói rõ là chưa có đủ thông tin trong hệ thống.\n"
            "Không tự suy diễn chẩn đoán, không bịa liều dùng, không thay thế tư vấn của bác sĩ.\n"
            "Nếu câu hỏi nhắc đến dấu hiệu nguy hiểm hoặc cấp cứu, hãy khuyên người dùng đi khám/cấp cứu ngay.\n"
            "Trả lời cùng ngôn ngữ với câu hỏi của người dùng.\n\n"
            f"Ngữ cảnh nội bộ:\n{context_text}\n\n"
            f"Câu hỏi người dùng: {state['question']}\n\n"
            "Hãy trả lời ngắn gọn, rõ ràng, bám sát dữ liệu."
        )

        response = await llm.ainvoke(prompt)
        state["answer"] = response.content if isinstance(response.content, str) else str(response.content)
        return state

    async def persist_chat_history(state: RagState) -> RagState:
        if mongodb.db is None:
            return state

        await mongodb.db[settings.rag_chat_history_collection].insert_one(
            {
                "session_id": state["session_id"],
                "question": state["question"],
                "answer": state["answer"],
                "used_context_count": len(state["contexts"]),
                "sources": state["sources"],
            }
        )
        return state

    graph_builder = StateGraph(RagState)
    graph_builder.add_node("load_context_from_postgres", load_context_from_postgres)
    graph_builder.add_node("generate_answer", generate_answer)
    graph_builder.add_node("persist_chat_history", persist_chat_history)
    graph_builder.add_edge(START, "load_context_from_postgres")
    graph_builder.add_edge("load_context_from_postgres", "generate_answer")
    graph_builder.add_edge("generate_answer", "persist_chat_history")
    graph_builder.add_edge("persist_chat_history", END)
    return graph_builder.compile()


async def run_rag(
    *,
    question: str,
    session_id: str,
    rag_service: MedicalRagService,
) -> dict[str, Any]:
    rag_graph = _build_rag_graph(rag_service)
    final_state = await rag_graph.ainvoke(
        {
            "question": question,
            "session_id": session_id,
            "contexts": [],
            "sources": [],
            "answer": "",
        }
    )
    return {
        "answer": final_state["answer"],
        "session_id": final_state["session_id"],
        "used_context_count": len(final_state["contexts"]),
        "sources": final_state["sources"],
    }
