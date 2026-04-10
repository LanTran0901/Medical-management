from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, TypedDict

from langchain_groq import ChatGroq
from langgraph.graph import END, START, StateGraph

from app.application.usecases.rag_usecases import MedicalRagService
from app.core.config import settings
from app.infrastructure.config.database.mongodb import connection as mongodb


class RagState(TypedDict):
    question: str
    user_id: str
    contexts: list[str]
    history_turns: list[dict[str, str]]
    sources: list[dict[str, Any]]
    answer: str


def _format_recent_history(history_turns: list[dict[str, str]]) -> str:
    if not history_turns:
        return "Khong co lich su hoi thoai truoc do."

    lines: list[str] = []
    for index, turn in enumerate(history_turns, start=1):
        question = str(turn.get("question", "")).strip()
        answer = str(turn.get("answer", "")).strip()
        if not question and not answer:
            continue
        lines.append(f"Luot {index} - Nguoi dung: {question or 'N/A'}")
        lines.append(f"Luot {index} - Tro ly: {answer or 'N/A'}")

    return "\n".join(lines) if lines else "Khong co lich su hoi thoai truoc do."


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

    async def load_recent_chat_history(state: RagState) -> RagState:
        state["history_turns"] = []
        if mongodb.db is None:
            return state

        cursor = (
            mongodb.db[settings.rag_chat_history_collection]
            .find(
                {"user_id": state["user_id"]},
                {"_id": 0, "question": 1, "answer": 1},
            )
            .sort("_id", -1)
            .limit(5)
        )
        rows = await cursor.to_list(length=5)
        rows.reverse()
        state["history_turns"] = [
            {
                "question": str(row.get("question", "")).strip(),
                "answer": str(row.get("answer", "")).strip(),
            }
            for row in rows
        ]
        return state

    async def generate_answer(state: RagState) -> RagState:
        if not state["contexts"] and not state["history_turns"]:
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

        history_text = _format_recent_history(state["history_turns"])
        context_text = "\n\n---\n\n".join(state["contexts"]) if state["contexts"] else "Khong co context moi o luot hien tai."
        prompt = (
            "Bạn là chatbot hỏi đáp y tế cho hệ thống Medical Management.\n"
            "Chi duoc tra loi dua tren lich su hoi thoai va ngữ cảnh nội bộ đã truy xuất bên dưới.\n"
            "Nếu dữ liệu không đủ để kết luận, hãy nói rõ là chưa có đủ thông tin trong hệ thống.\n"
            "Không tự suy diễn chẩn đoán, không bịa liều dùng, không thay thế tư vấn của bác sĩ.\n"
            "Nếu câu hỏi nhắc đến dấu hiệu nguy hiểm hoặc cấp cứu, hãy khuyên người dùng đi khám/cấp cứu ngay.\n"
            "Trả lời cùng ngôn ngữ với câu hỏi của người dùng.\n\n"
            f"Lich su hoi thoai gan day (toi da 5 luot):\n{history_text}\n\n"
            f"Ngữ cảnh nội bộ truy xuất ở lượt hiện tại:\n{context_text}\n\n"
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
                "user_id": state["user_id"],
                "question": state["question"],
                "answer": state["answer"],
                "used_context_count": len(state["contexts"]),
                "sources": state["sources"],
                "created_at": datetime.now(timezone.utc),
            }
        )
        return state

    graph_builder = StateGraph(RagState)
    graph_builder.add_node("load_context_from_postgres", load_context_from_postgres)
    graph_builder.add_node("load_recent_chat_history", load_recent_chat_history)
    graph_builder.add_node("generate_answer", generate_answer)
    graph_builder.add_node("persist_chat_history", persist_chat_history)
    graph_builder.add_edge(START, "load_context_from_postgres")
    graph_builder.add_edge("load_context_from_postgres", "load_recent_chat_history")
    graph_builder.add_edge("load_recent_chat_history", "generate_answer")
    graph_builder.add_edge("generate_answer", "persist_chat_history")
    graph_builder.add_edge("persist_chat_history", END)
    return graph_builder.compile()


async def run_rag(
    *,
    question: str,
    user_id: str,
    rag_service: MedicalRagService,
) -> dict[str, Any]:
    rag_graph = _build_rag_graph(rag_service)
    final_state = await rag_graph.ainvoke(
        {
            "question": question,
            "user_id": user_id,
            "contexts": [],
            "history_turns": [],
            "sources": [],
            "answer": "",
        }
    )
    return {
        "answer": final_state["answer"],
        "used_context_count": len(final_state["contexts"]),
        "sources": final_state["sources"],
    }
